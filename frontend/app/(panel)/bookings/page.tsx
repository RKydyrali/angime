"use client";

import { useMemo, useState, Fragment } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { addDays, format, startOfWeek } from "date-fns";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/booking-status-badge";
import { Badge } from "@/components/ui/badge";
import { CaretLeft, CaretRight, CalendarDots, Plus } from "@phosphor-icons/react";

interface Booking {
  id: string;
  service_id: string | null;
  client_name: string;
  client_phone: string;
  date: string;
  time: string;
  duration_min: number;
  status: string;
  notes: string;
  source: string;
  service_name_ru: string | null;
  service_name_kz: string | null;
}

interface Service {
  id: string;
  name_ru: string;
  name_kz: string;
  price: number;
  duration_min: number;
  is_active: boolean;
}

const DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
const DEFAULT_OPEN = "09:00";
const DEFAULT_CLOSE = "20:00";
const SLOT_STEP = 60;

function slotsBetween(open: string, close: string): string[] {
  const [oh, om] = open.split(":").map(Number);
  const [ch, cm] = close.split(":").map(Number);
  const slots: string[] = [];
  let cur = oh * 60 + om;
  const end = ch * 60 + cm;
  while (cur + SLOT_STEP <= end) {
    const h = Math.floor(cur / 60);
    const m = cur % 60;
    slots.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
    cur += SLOT_STEP;
  }
  return slots;
}

function bookingForSlot(bookings: Booking[], slot: string): Booking[] {
  return bookings.filter((b) => b.time.slice(0, 5) >= slot && b.time.slice(0, 5) < addMinutes(slot, SLOT_STEP));
}

function addMinutes(slot: string, mins: number): string {
  const [h, m] = slot.split(":").map(Number);
  const t = h * 60 + m + mins;
  return `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
}

export default function BookingsPage() {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const [weekStart, setWeekStart] = useState<Date>(() =>
    startOfWeek(new Date(), { weekStartsOn: 1 })
  );
  const [selected, setSelected] = useState<{ date: string; slot: string; bookings: Booking[] } | null>(null);
  const [details, setDetails] = useState<Booking | null>(null);
  const [newOpen, setNewOpen] = useState(false);
  const [form, setForm] = useState({
    service_id: "",
    client_name: "",
    client_phone: "",
    date: "",
    time: "10:00",
    notes: "",
  });

  const fromDate = format(weekStart, "yyyy-MM-dd");
  const toDate = format(addDays(weekStart, 6), "yyyy-MM-dd");

  const { data: settings } = useQuery({
    queryKey: ["tenant-me"],
    queryFn: () => api<{ business_hours: Record<string, { open?: string; close?: string } | null> }>("/api/tenant/me"),
  });
  const { data: services } = useQuery({
    queryKey: ["services"],
    queryFn: () => api<Service[]>("/api/tenant/services"),
  });
  const { data: bookings, isLoading } = useQuery({
    queryKey: ["bookings", fromDate, toDate],
    queryFn: () => api<Booking[]>(`/api/tenant/bookings?from_date=${fromDate}&to_date=${toDate}`),
  });

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart]
  );

  const byDate = useMemo(() => {
    const m: Record<string, Booking[]> = {};
    for (const b of bookings || []) {
      (m[b.date] = m[b.date] || []).push(b);
    }
    return m;
  }, [bookings]);

  // часовой диапазон из настроек или дефолт
  const range = useMemo(() => {
    const hours = settings?.business_hours || {};
    const key = DAY_KEYS[(weekStart.getDay() + 6) % 7];
    const day = hours[key];
    const open = day?.open || DEFAULT_OPEN;
    const close = day?.close || DEFAULT_CLOSE;
    return { open, close };
  }, [settings, weekStart]);

  const slots = useMemo(() => slotsBetween(range.open, range.close), [range]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["bookings"] });
    qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  };

  const statusMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api<Booking>(`/api/tenant/bookings/${id}`, { method: "PATCH", body: { status } }),
    onSuccess: () => {
      invalidate();
      setDetails(null);
      toast.success(t("st_saved"));
    },
  });

  const createMut = useMutation({
    mutationFn: () =>
      api<Booking>("/api/tenant/bookings", {
        method: "POST",
        body: {
          service_id: form.service_id || null,
          client_name: form.client_name,
          client_phone: form.client_phone,
          date: form.date,
          time: form.time,
          notes: form.notes,
        },
      }),
    onSuccess: () => {
      invalidate();
      setNewOpen(false);
      setForm({ service_id: "", client_name: "", client_phone: "", date: "", time: "10:00", notes: "" });
      toast.success(t("st_saved"));
    },
  });

  const svcName = (b: Booking) =>
    lang === "kz" && b.service_name_kz ? b.service_name_kz : b.service_name_ru;

  const weekLabel = `${format(weekStart, "dd.MM")} — ${format(addDays(weekStart, 6), "dd.MM")}`;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("bk_title")}</h1>
          <p className="text-sm text-muted-foreground">{weekLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setWeekStart(addDays(weekStart, -7))}>
            <CaretLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }))}
          >
            {t("bk_today")}
          </Button>
          <Button variant="outline" size="icon" onClick={() => setWeekStart(addDays(weekStart, 7))}>
            <CaretRight className="h-4 w-4" />
          </Button>
          <Button className="gap-2" onClick={() => { setForm({ ...form, date: format(new Date(), "yyyy-MM-dd") }); setNewOpen(true); }}>
            <Plus className="h-4 w-4" /> {t("bk_new")}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-[480px] w-full rounded-xl" />
      ) : (
        <>
          {/* DESKTOP: time-slot grid */}
          <Card className="hidden overflow-x-auto md:block">
            <div className="min-w-[720px]">
              <div className="grid" style={{ gridTemplateColumns: "64px repeat(7, 1fr)" }}>
                <div className="border-b border-r" />
                {days.map((d) => {
                  const key = DAY_KEYS[(d.getDay() + 6) % 7];
                  const isToday = format(d, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd");
                  return (
                    <div key={d.toISOString()} className={`border-b p-2 text-center ${isToday ? "bg-primary/5" : ""}`}>
                      <p className="text-xs font-medium text-muted-foreground">
                        {lang === "kz" ? KZ_DAYS[(d.getDay() + 6) % 7] : RU_DAYS[(d.getDay() + 6) % 7]}
                      </p>
                      <p className={`text-lg font-bold ${isToday ? "text-primary" : ""}`}>
                        {format(d, "dd")}
                      </p>
                      {!settings?.business_hours?.[key]?.open && (
                        <Badge variant="secondary" className="mt-1">{t("bk_closed")}</Badge>
                      )}
                    </div>
                  );
                })}

                {slots.map((slot) => (
                  <Fragment key={slot}>
                    <div className="flex items-start justify-end border-b border-r pr-2 pt-2 text-xs font-medium text-muted-foreground">
                      {slot}
                    </div>
                    {days.map((d) => {
                      const key = DAY_KEYS[(d.getDay() + 6) % 7];
                      const ds = format(d, "yyyy-MM-dd");
                      const dayBookings = bookingForSlot(byDate[ds] || [], slot);
                      const closed = !settings?.business_hours?.[key]?.open;
                      return (
                        <button
                          key={ds + slot}
                          onClick={() =>
                            setSelected({ date: ds, slot, bookings: dayBookings })
                          }
                          className={`min-h-[52px] border-b border-r p-1 text-left transition hover:bg-accent/50 ${closed ? "bg-muted/40" : ""}`}
                        >
                          {dayBookings.map((b) => (
                            <div
                              key={b.id}
                              onClick={(e) => {
                                e.stopPropagation();
                                setDetails(b);
                              }}
                              className={`mb-1 cursor-pointer truncate rounded-md px-1.5 py-0.5 text-[11px] font-medium ${
                                b.status === "cancelled"
                                  ? "bg-red-100 text-red-600 line-through"
                                  : b.status === "completed"
                                  ? "bg-sky-100 text-sky-700"
                                  : "bg-primary/10 text-primary"
                              }`}
                            >
                              {b.time.slice(0, 5)} {svcName(b) || b.client_name}
                            </div>
                          ))}
                        </button>
                      );
                    })}
                  </Fragment>
                ))}
              </div>
            </div>
          </Card>

          {/* MOBILE: day tabs + list */}
          <div className="md:hidden">
            <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
              {days.map((d) => {
                const isToday = format(d, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd");
                return (
                  <Button
                    key={d.toISOString()}
                    variant="outline"
                    size="sm"
                    className={isToday ? "border-primary text-primary" : ""}
                    onClick={() => setSelected({ date: format(d, "yyyy-MM-dd"), slot: "", bookings: byDate[format(d, "yyyy-MM-dd")] || [] })}
                  >
                    {lang === "kz" ? KZ_DAYS[(d.getDay() + 6) % 7] : RU_DAYS[(d.getDay() + 6) % 7]} {format(d, "dd")}
                  </Button>
                );
              })}
            </div>
            {selected ? (
              <Card className="p-4">
                <p className="mb-3 font-medium">
                  {format(new Date(selected.date), "dd.MM")} — {selected.slot || t("bk_title")}
                </p>
                {selected.bookings.length === 0 ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">{t("bk_no_bookings")}</p>
                ) : (
                  <div className="space-y-2">
                    {selected.bookings.map((b) => (
                      <button
                        key={b.id}
                        onClick={() => setDetails(b)}
                        className="flex w-full items-center justify-between rounded-xl border p-3 text-left"
                      >
                        <div>
                          <p className="text-sm font-medium">{svcName(b) || "—"}</p>
                          <p className="text-xs text-muted-foreground">
                            {b.time.slice(0, 5)} · {b.client_name}
                          </p>
                        </div>
                        <StatusBadge status={b.status} />
                      </button>
                    ))}
                  </div>
                )}
              </Card>
            ) : (
              <p className="text-center text-sm text-muted-foreground">{t("bk_no_bookings")}</p>
            )}
          </div>
        </>
      )}

      {/* DETAILS DIALOG */}
      <Dialog open={!!details} onOpenChange={(o) => !o && setDetails(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarDots weight="duotone" className="h-5 w-5 text-primary" />
              {t("bk_details")}
            </DialogTitle>
          </DialogHeader>
          {details && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-muted-foreground">{t("bk_client")}</Label>
                  <p className="font-medium">{details.client_name}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">{t("bk_service")}</Label>
                  <p className="font-medium">{svcName(details) || "—"}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">{t("date")}</Label>
                  <p className="font-medium">{format(new Date(details.date), "dd.MM.yyyy")}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">{t("time")}</Label>
                  <p className="font-medium">{details.time.slice(0, 5)}</p>
                </div>
                {details.client_phone && (
                  <div>
                    <Label className="text-muted-foreground">{t("phone")}</Label>
                    <p className="font-medium">{details.client_phone}</p>
                  </div>
                )}
                <div>
                  <Label className="text-muted-foreground">{t("bk_source")}</Label>
                  <p className="font-medium capitalize">{details.source}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Label>{t("status")}</Label>
                <Select
                  value={details.status}
                  onValueChange={(v) => statusMut.mutate({ id: details.id, status: v })}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="confirmed">{t("bk_status_confirmed")}</SelectItem>
                    <SelectItem value="completed">{t("bk_status_completed")}</SelectItem>
                    <SelectItem value="cancelled">{t("bk_status_cancelled")}</SelectItem>
                    <SelectItem value="no_show">{t("bk_status_no_show")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDetails(null)}>
                  {t("close")}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* NEW BOOKING DIALOG */}
      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("bk_new")}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="space-y-2">
              <Label>{t("bk_service")}</Label>
              <Select value={form.service_id} onValueChange={(v) => setForm({ ...form, service_id: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {services?.filter((s) => s.is_active).map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {lang === "kz" && s.name_kz ? s.name_kz : s.name_ru} — {s.price} ₸
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>{t("bk_client")}</Label>
                <Input
                  value={form.client_name}
                  onChange={(e) => setForm({ ...form, client_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("phone")}</Label>
                <Input
                  value={form.client_phone}
                  onChange={(e) => setForm({ ...form, client_phone: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("date")}</Label>
                <Input
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("time")}</Label>
                <Select value={form.time} onValueChange={(v) => setForm({ ...form, time: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {slots.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOpen(false)}>
              {t("cancel")}
            </Button>
            <Button
              onClick={() => createMut.mutate()}
              disabled={!form.client_name || !form.date || createMut.isPending}
            >
              {t("save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const RU_DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const KZ_DAYS = ["Дс", "Сс", "Ср", "Бс", "Жм", "Сб", "Жс"];
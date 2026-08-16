"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Plus,
  PencilSimple,
  Trash,
  Clock,
  Coins,
} from "@phosphor-icons/react";

interface Service {
  id: string;
  name_ru: string;
  name_kz: string;
  description_ru: string;
  description_kz: string;
  price: number;
  duration_min: number;
  is_active: boolean;
  daily_limit: number;
}

const EMPTY: Service = {
  id: "",
  name_ru: "",
  name_kz: "",
  description_ru: "",
  description_kz: "",
  price: 0,
  duration_min: 60,
  is_active: true,
  daily_limit: 0,
};

export default function ServicesPage() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Service | null>(null);
  const [form, setForm] = useState<Service>(EMPTY);

  const { data, isLoading } = useQuery({
    queryKey: ["services"],
    queryFn: () => api<Service[]>("/api/tenant/services"),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["services"] });

  const saveMut = useMutation({
    mutationFn: (s: Service) => {
      const body = {
        name_ru: s.name_ru,
        name_kz: s.name_kz,
        description_ru: s.description_ru,
        description_kz: s.description_kz,
        price: s.price,
        duration_min: s.duration_min,
        is_active: s.is_active,
        daily_limit: s.daily_limit,
      };
      return editing
        ? api<Service>(`/api/tenant/services/${editing.id}`, { method: "PATCH", body })
        : api<Service>("/api/tenant/services", { method: "POST", body });
    },
    onSuccess: () => {
      invalidate();
      setDialogOpen(false);
      toast.success(t("st_saved"));
    },
  });

  const delMut = useMutation({
    mutationFn: (id: string) => api(`/api/tenant/services/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      invalidate();
      toast.success(t("ad_deleted"));
    },
  });

  const openNew = () => {
    setEditing(null);
    setForm(EMPTY);
    setDialogOpen(true);
  };

  const openEdit = (s: Service) => {
    setEditing(s);
    setForm(s);
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("svc_title")}</h1>
        </div>
        <Button onClick={openNew} className="gap-2">
          <Plus className="h-4 w-4" /> {t("svc_add")}
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : !data?.length ? (
        <div className="rounded-xl border border-dashed p-12 text-center text-sm text-muted-foreground">
          {t("svc_empty")}
        </div>
      ) : (
        <div className="rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("name")}</TableHead>
                <TableHead>{t("price")}</TableHead>
                <TableHead>{t("svc_duration")}</TableHead>
                <TableHead>{t("svc_daily_limit")}</TableHead>
                <TableHead>{t("status")}</TableHead>
                <TableHead className="text-right">{t("actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{s.name_ru}</p>
                      {s.name_kz && (
                        <p className="text-xs text-muted-foreground">{s.name_kz}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-medium">
                    {s.price.toLocaleString("ru-RU")} ₸
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" /> {s.duration_min} мин
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {s.daily_limit > 0 ? s.daily_limit : "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={s.is_active ? "default" : "secondary"}>
                      {s.is_active ? t("active") : t("inactive")}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(s)}>
                        <PencilSimple className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        onClick={() => delMut.mutate(s.id)}
                      >
                        <Trash className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? t("edit") : t("svc_add")}</DialogTitle>
            <DialogDescription>
              {t("svc_bot_visible")}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>{t("svc_name_ru")}</Label>
                <Input
                  value={form.name_ru}
                  onChange={(e) => setForm({ ...form, name_ru: e.target.value })}
                  placeholder="Стрижка"
                />
              </div>
              <div className="space-y-2">
                <Label>{t("svc_name_kz")}</Label>
                <Input
                  value={form.name_kz}
                  onChange={(e) => setForm({ ...form, name_kz: e.target.value })}
                  placeholder="Шаш қию"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>{t("svc_desc_ru")}</Label>
                <Textarea
                  value={form.description_ru}
                  onChange={(e) => setForm({ ...form, description_ru: e.target.value })}
                  rows={2}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("svc_desc_kz")}</Label>
                <Textarea
                  value={form.description_kz}
                  onChange={(e) => setForm({ ...form, description_kz: e.target.value })}
                  rows={2}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label>{t("price")}</Label>
                <div className="relative">
                  <Input
                    type="number"
                    value={form.price}
                    onChange={(e) => setForm({ ...form, price: Number(e.target.value) })}
                  />
                  <Coins className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>{t("svc_duration")}</Label>
                <Input
                  type="number"
                  value={form.duration_min}
                  onChange={(e) => setForm({ ...form, duration_min: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("svc_daily_limit")}</Label>
                <Input
                  type="number"
                  value={form.daily_limit}
                  onChange={(e) => setForm({ ...form, daily_limit: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="flex items-center justify-between rounded-xl border p-3">
              <Label>{t("active")}</Label>
              <Switch
                checked={form.is_active}
                onCheckedChange={(v) => setForm({ ...form, is_active: v })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              {t("cancel")}
            </Button>
            <Button
              onClick={() => saveMut.mutate(form)}
              disabled={!form.name_ru || saveMut.isPending}
            >
              {t("save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
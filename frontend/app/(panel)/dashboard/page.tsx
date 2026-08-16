"use client";

import { useQuery } from "@tanstack/react-query";
import { useI18n } from "@/lib/i18n";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Bar, BarChart, XAxis, YAxis, CartesianGrid } from "recharts";
import { AiChat } from "@/components/ai-chat";
import { StatusBadge } from "@/components/booking-status-badge";
import {
  CalendarDots,
  CalendarX,
  ChatCircleDots,
  Coins,
  ArrowUpRight,
} from "@phosphor-icons/react";
import { format } from "date-fns";

interface Stats {
  bookings_today: number;
  bookings_week: number;
  new_conversations_7d: number;
  revenue_estimate_week: number;
  upcoming: Booking[];
  week_chart: { date: string; count: number }[];
  subscription_status: string;
  paid_until: string | null;
}

interface Booking {
  id: string;
  client_name: string;
  service_name_ru: string | null;
  service_name_kz: string | null;
  date: string;
  time: string;
  status: string;
  price?: number;
}

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon weight="duotone" className="h-5 w-5" />
          </div>
        </div>
        <p className="mt-2 text-3xl font-bold tracking-tight">{value}</p>
        {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { t, lang } = useI18n();
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => api<Stats>("/api/tenant/stats/dashboard"),
  });

  const chartData = (data?.week_chart || []).map((d) => ({
    date: format(new Date(d.date), lang === "kz" ? "dd.MM" : "dd.MM"),
    count: d.count,
  }));

  const subActive = data?.subscription_status === "active" || data?.subscription_status === "trial";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("dash_title")}</h1>
        <p className="text-sm text-muted-foreground">
          {format(new Date(), lang === "kz" ? "dd.MM.yyyy" : "dd.MM.yyyy")}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[110px] rounded-xl" />
          ))
        ) : (
          <>
            <StatCard icon={CalendarDots} label={t("dash_today")} value={data?.bookings_today ?? 0} />
            <StatCard icon={CalendarX} label={t("dash_week")} value={data?.bookings_week ?? 0} />
            <StatCard icon={ChatCircleDots} label={t("dash_chats")} value={data?.new_conversations_7d ?? 0} />
            <StatCard
              icon={Coins}
              label={t("dash_revenue")}
              value={`${(data?.revenue_estimate_week ?? 0).toLocaleString("ru-RU")} ₸`}
            />
          </>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t("dash_week_chart")}</CardTitle>
            <CardDescription>
              {data ? `${data.bookings_week} ${t("bk_title").toLowerCase()}` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-[220px] w-full rounded-xl" />
            ) : (
              <ChartContainer
                config={{
                  count: { label: "count", color: "var(--chart-1)" },
                }}
                className="h-[220px] w-full"
              >
                <BarChart data={chartData}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" />
                  <XAxis dataKey="date" tickLine={false} axisLine={false} fontSize={12} />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} width={24} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]} fill="var(--color-count)" maxBarSize={40} />
                </BarChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("dash_sub_status")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {data?.paid_until ? (
              <div className="flex items-center justify-between rounded-xl border p-4">
                <div>
                  <p className="text-sm text-muted-foreground">
                    {subActive ? t("dash_sub_active") : t("dash_sub_expired")}
                  </p>
                  <p className="mt-1 text-lg font-semibold">
                    {format(new Date(data.paid_until), "dd.MM.yyyy")}
                  </p>
                </div>
                <Badge variant={subActive ? "default" : "destructive"}>
                  {subActive ? t("active") : t("inactive")}
                </Badge>
              </div>
            ) : (
              <Badge variant="secondary">{data?.subscription_status}</Badge>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{t("dash_upcoming")}</CardTitle>
          <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-24 w-full rounded-xl" />
          ) : data?.upcoming.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {t("dash_no_bookings")}
            </p>
          ) : (
            <div className="divide-y">
              {data?.upcoming.slice(0, 6).map((b) => (
                <div key={b.id} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <CalendarDots weight="duotone" className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {b.service_name_kz && lang === "kz" ? b.service_name_kz : b.service_name_ru || "—"}
                      </p>
                      <p className="text-xs text-muted-foreground">{b.client_name}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">
                      {format(new Date(b.date), "dd.MM")} · {b.time.slice(0, 5)}
                    </span>
                    <StatusBadge status={b.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <AiChat />
    </div>
  );
}
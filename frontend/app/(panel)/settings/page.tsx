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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Clock,
  Translate,
  BellRinging,
  TelegramLogo,
  WhatsappLogo,
  CheckCircle,
  Key,
  PaperPlaneTilt,
} from "@phosphor-icons/react";

const DAYS = [
  { key: "mon", ru: "Понедельник", kz: "Дүйсенбі" },
  { key: "tue", ru: "Вторник", kz: "Сейсенбі" },
  { key: "wed", ru: "Среда", kz: "Сәрсенбі" },
  { key: "thu", ru: "Четверг", kz: "Бейсенбі" },
  { key: "fri", ru: "Пятница", kz: "Жұма" },
  { key: "sat", ru: "Суббота", kz: "Сенбі" },
  { key: "sun", ru: "Воскресенье", kz: "Жексенбі" },
] as const;

interface Settings {
  id: string;
  name: string;
  business_hours: Record<string, { open: string; close: string } | null>;
  knowledge_ru: string;
  knowledge_kz: string;
  greeting_enabled: boolean;
  reminder_enabled: boolean;
  reminder_hours_before: number;
  whatsapp_connected: boolean;
  subscription_status: string;
  paid_until: string | null;
}

export default function SettingsPage() {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const [hours, setHours] = useState<Settings["business_hours"] | null>(null);
  const [knowledgeRu, setKnowledgeRu] = useState("");
  const [knowledgeKz, setKnowledgeKz] = useState("");
  const [greeting, setGreeting] = useState(true);
  const [reminderEnabled, setReminderEnabled] = useState(true);
  const [reminderHours, setReminderHours] = useState(1);
  const [tgCode, setTgCode] = useState<string | null>(null);

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      const s = await api<Settings>("/api/tenant/me");
      setHours(s.business_hours);
      setKnowledgeRu(s.knowledge_ru);
      setKnowledgeKz(s.knowledge_kz);
      setGreeting(s.greeting_enabled);
      setReminderEnabled(s.reminder_enabled);
      setReminderHours(s.reminder_hours_before);
      return s;
    },
  });

  const saveMut = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<Settings>("/api/tenant/settings", { method: "PATCH", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      qc.invalidateQueries({ queryKey: ["tenant-me"] });
      toast.success(t("st_saved"));
    },
  });

  const saveHours = () => saveMut.mutate({ business_hours: hours });
  const saveKnowledge = () =>
    saveMut.mutate({ knowledge_ru: knowledgeRu, knowledge_kz: knowledgeKz });
  const saveBehavior = () =>
    saveMut.mutate({
      greeting_enabled: greeting,
      reminder_enabled: reminderEnabled,
      reminder_hours_before: reminderHours,
    });

  const { data: notif } = useQuery({
    queryKey: ["notifications"],
    queryFn: () =>
      api<{ linked: boolean; tg_chat_id: string; tg_username: string; linked_at: string | null }>(
        "/api/tenant/notifications"
      ),
  });

  const codeMut = useMutation({
    mutationFn: () => api<{ code: string }>("/api/tenant/notifications/code", { method: "POST" }),
    onSuccess: (d) => setTgCode(d.code),
  });

  const testMut = useMutation({
    mutationFn: () => api("/api/tenant/notifications/test", { method: "POST" }),
    onSuccess: () => toast.success(t("ad_test_msg_sent")),
    onError: () => toast.error(t("ad_test_msg_fail")),
  });

  const dayLabel = (k: string) => {
    const d = DAYS.find((x) => x.key === k)!;
    return lang === "kz" ? d.kz : d.ru;
  };
  const isSubActive = settings
    ? settings.subscription_status === "active" ||
      settings.subscription_status === "trial"
    : false;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">{t("st_title")}</h1>

      {isLoading || !settings ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-xl" />
          ))}
        </div>
      ) : (
        <></>
      )}

      {!isLoading && settings ? (
        <>
      {/* Business hours */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock weight="duotone" className="h-5 w-5 text-primary" /> {t("st_hours")}
          </CardTitle>
          <CardDescription>{t("st_hours_desc")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {DAYS.map((d) => {
            const day = hours?.[d.key] || null;
            const isOff = !day || !day.open;
            return (
              <div key={d.key} className="flex flex-wrap items-center gap-3">
                <div className="w-40 text-sm font-medium">{dayLabel(d.key)}</div>
                <Switch
                  checked={!isOff}
                  onCheckedChange={(v) =>
                    setHours({
                      ...(hours || {}),
                      [d.key]: v ? { open: "09:00", close: "18:00" } : null,
                    })
                  }
                />
                {isOff ? (
                  <span className="text-sm text-muted-foreground">{t("st_day_off")}</span>
                ) : (
                  <div className="flex items-center gap-2">
                    <Input
                      type="time"
                      className="w-28"
                      value={day?.open}
                      onChange={(e) =>
                        setHours({
                          ...(hours || {}),
                          [d.key]: { ...(day || {}), open: e.target.value },
                        })
                      }
                    />
                    <span className="text-muted-foreground">—</span>
                    <Input
                      type="time"
                      className="w-28"
                      value={day?.close}
                      onChange={(e) =>
                        setHours({
                          ...(hours || {}),
                          [d.key]: { ...(day || {}), close: e.target.value },
                        })
                      }
                    />
                  </div>
                )}
              </div>
            );
          })}
          <div className="pt-2">
            <Button onClick={saveHours} disabled={saveMut.isPending}>
              {t("save")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Bot knowledge */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Translate weight="duotone" className="h-5 w-5 text-primary" /> {t("st_knowledge")}
          </CardTitle>
          <CardDescription>{t("st_knowledge_desc")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label>{t("st_knowledge_ru")}</Label>
            <Textarea
              rows={8}
              value={knowledgeRu}
              onChange={(e) => setKnowledgeRu(e.target.value)}
              placeholder="Адрес, услуги, цены, правила, акции..."
            />
          </div>
          <div className="space-y-2">
            <Label>{t("st_knowledge_kz")}</Label>
            <Textarea
              rows={8}
              value={knowledgeKz}
              onChange={(e) => setKnowledgeKz(e.target.value)}
              placeholder="Мекенжай, қызметтер, бағалар, ережелер..."
            />
          </div>
          <div className="md:col-span-2">
            <Button onClick={saveKnowledge} disabled={saveMut.isPending}>
              {t("save")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Behavior */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BellRinging weight="duotone" className="h-5 w-5 text-primary" /> {t("st_reminders")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>{t("st_reminders_enabled")}</Label>
            </div>
            <Switch checked={reminderEnabled} onCheckedChange={setReminderEnabled} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label>{t("st_reminders_hours")}</Label>
            </div>
            <Input
              type="number"
              className="w-24"
              min={1}
              max={72}
              value={reminderHours}
              onChange={(e) => setReminderHours(Number(e.target.value))}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label>{t("st_greetings_enabled")}</Label>
            </div>
            <Switch checked={greeting} onCheckedChange={setGreeting} />
          </div>
          <Button onClick={saveBehavior} disabled={saveMut.isPending}>
            {t("save")}
          </Button>
        </CardContent>
      </Card>

      {/* WhatsApp + Subscription */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <WhatsappLogo weight="duotone" className="h-5 w-5 text-primary" /> {t("st_wa")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-xl border p-3">
              <span className="text-sm">{t("st_wa_status")}</span>
              <Badge variant={settings.whatsapp_connected ? "default" : "secondary"}>
                {settings.whatsapp_connected ? t("st_wa_connected") : t("st_wa_not_connected")}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle weight="duotone" className="h-5 w-5 text-primary" /> {t("st_sub")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between rounded-xl border p-3">
              <div>
                <p className="text-sm text-muted-foreground">
                  {isSubActive ? t("dash_sub_active") : t("dash_sub_expired")}
                </p>
                {settings.paid_until ? (
                  <p className="mt-1 text-lg font-semibold">
                    {new Date(settings.paid_until).toLocaleDateString("ru-RU")}
                  </p>
                ) : null}
              </div>
              <Badge variant={isSubActive ? "default" : "destructive"}>
                {isSubActive ? t("active") : t("inactive")}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Telegram connect */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TelegramLogo weight="duotone" className="h-5 w-5 text-primary" /> {t("st_tg")}
          </CardTitle>
          <CardDescription>{t("st_tg_how")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {notif?.linked ? (
            <Alert>
              <CheckCircle className="h-4 w-4 text-primary" />
              <AlertDescription>
                {t("st_tg_linked")} — {notif.tg_username || notif.tg_chat_id}
              </AlertDescription>
            </Alert>
          ) : (
            <Alert>
              <Key className="h-4 w-4" />
              <AlertDescription>{t("st_tg_not_linked")}</AlertDescription>
            </Alert>
          )}

          {tgCode ? (
            <div className="rounded-xl border-2 border-dashed border-primary p-6 text-center">
              <p className="text-sm text-muted-foreground">{t("st_tg_code_desc")}</p>
              <p className="my-4 text-5xl font-extrabold tracking-[0.3em] text-primary">{tgCode}</p>
              <Badge variant="secondary">{t("st_tg_code_title")}</Badge>
            </div>
          ) : (
            <Button onClick={() => codeMut.mutate()} disabled={codeMut.isPending} className="gap-2">
              <Key className="h-4 w-4" /> {t("st_tg_code_btn")}
            </Button>
          )}

          {notif?.linked && (
            <Button variant="outline" onClick={() => testMut.mutate()} disabled={testMut.isPending} className="gap-2">
              <PaperPlaneTilt className="h-4 w-4" /> {t("st_tg_test")}
            </Button>
          )}
        </CardContent>
      </Card>

      <Separator />
        </>
      ) : null}
    </div>
  );
}
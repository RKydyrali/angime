"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import {
  Plus,
  Users,
  ShieldCheck,
  CalendarCheck,
  CalendarPlus,
  Key,
  WhatsappLogo,
  PaperPlaneTilt,
  SignIn,
  Trash,
  WarningCircle,
  Copy,
} from "@phosphor-icons/react";

interface Tenant {
  id: string;
  name: string;
  slug: string;
  contact_phone: string;
  login_email: string | null;
  whatsapp_connected: boolean;
  subscription_status: string;
  paid_until: string | null;
  created_at: string;
}

interface AdminStats {
  tenants_total: number;
  tenants_active: number;
  bookings_30d: number;
  tenants_expiring_soon: Tenant[];
}

const EMPTY_FORM = {
  name: "",
  slug: "",
  login_email: "",
  password: "",
  contact_phone: "",
  subscription_price: 20000,
  months_paid: 1,
};

export default function AdminPage() {
  const { t, lang } = useI18n();
  const { auth, loginAsTenant } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();

  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [extendTenant, setExtendTenant] = useState<Tenant | null>(null);
  const [extendMonths, setExtendMonths] = useState(1);
  const [credsTenant, setCredsTenant] = useState<Tenant | null>(null);
  const [creds, setCreds] = useState({
    phone_number_id: "",
    access_token: "",
    app_secret: "",
    verify_token: "",
    business_name: "",
  });
  const [testWa, setTestWa] = useState("");
  const [tgTenant, setTgTenant] = useState<Tenant | null>(null);
  const [tgCode, setTgCode] = useState("");

  const { data: tenants, isLoading } = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => api<Tenant[]>("/api/admin/tenants"),
  });
  const { data: stats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => api<AdminStats>("/api/admin/stats"),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin-tenants"] });
    qc.invalidateQueries({ queryKey: ["admin-stats"] });
  };

  const createMut = useMutation({
    mutationFn: () =>
      api<Tenant>("/api/admin/tenants", {
        method: "POST",
        body: {
          ...form,
          subscription_price: Number(form.subscription_price),
          months_paid: Number(form.months_paid),
          login_email: form.login_email || null,
          password: form.password || null,
        },
      }),
    onSuccess: () => {
      invalidate();
      setAddOpen(false);
      setForm(EMPTY_FORM);
      toast.success(t("ad_created"));
    },
    onError: (e) => toast.error(String(e)),
  });

  const extendMut = useMutation({
    mutationFn: () =>
      api(`/api/admin/tenants/${extendTenant?.id}/subscription`, {
        method: "POST",
        body: { months: Number(extendMonths) },
      }),
    onSuccess: () => {
      invalidate();
      setExtendTenant(null);
      toast.success(t("st_saved"));
    },
  });

  const credsMut = useMutation({
    mutationFn: () =>
      api(`/api/admin/tenants/${credsTenant?.id}/meta-creds`, {
        method: "POST",
        body: creds,
      }),
    onSuccess: () => {
      invalidate();
      toast.success(t("st_saved"));
    },
  });

  const testMut = useMutation({
    mutationFn: () =>
      api(`/api/admin/tenants/${credsTenant?.id}/test-message`, {
        method: "POST",
        body: { wa_id: testWa },
      }),
    onSuccess: () => toast.success(t("ad_test_msg_sent")),
    onError: () => toast.error(t("ad_test_msg_fail")),
  });

  const tgCodeMut = useMutation({
    mutationFn: () =>
      api<{ code: string }>(`/api/admin/tenants/${tgTenant?.id}/tg-code`, { method: "POST" }),
    onSuccess: (d) => setTgCode(d.code),
  });

  const delMut = useMutation({
    mutationFn: (id: string) => api(`/api/admin/tenants/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      invalidate();
      toast.success(t("ad_deleted"));
    },
  });

  const copyCode = () => {
    navigator.clipboard?.writeText(tgCode);
    toast.success(t("st_saved"));
  };

  if (auth.role !== "admin") {
    return (
      <div className="flex h-64 items-center justify-center">
        <Badge variant="secondary">{t("login_admin")}</Badge>
      </div>
    );
  }

  const subBadge = (s: string) => {
    if (s === "active" || s === "trial")
      return <Badge>{t("active")}</Badge>;
    return <Badge variant="destructive">{t("inactive")}</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">{t("ad_title")}</h1>
        <Button className="gap-2" onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4" /> {t("ad_add_client")}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Users weight="duotone" className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.tenants_total ?? "—"}</p>
              <p className="text-sm text-muted-foreground">{t("ad_stats_tenants")}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ShieldCheck weight="duotone" className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.tenants_active ?? "—"}</p>
              <p className="text-sm text-muted-foreground">{t("ad_stats_active")}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <CalendarCheck weight="duotone" className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.bookings_30d ?? "—"}</p>
              <p className="text-sm text-muted-foreground">{t("ad_stats_bookings")}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {stats && stats.tenants_expiring_soon.length > 0 && (
        <Alert>
          <WarningCircle className="h-4 w-4" />
          <AlertDescription>
            {t("ad_expiring")}:{" "}
            {stats.tenants_expiring_soon.map((x) => x.name).join(", ")}
          </AlertDescription>
        </Alert>
      )}

      {/* Tenants table */}
      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-xl" />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("ad_name")}</TableHead>
                  <TableHead>{t("ad_sub_status")}</TableHead>
                  <TableHead>{t("ad_paid_until")}</TableHead>
                  <TableHead>WhatsApp</TableHead>
                  <TableHead className="text-right">{t("actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants?.map((tn) => (
                  <TableRow key={tn.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{tn.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {tn.login_email || tn.slug}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{subBadge(tn.subscription_status)}</TableCell>
                    <TableCell>
                      {tn.paid_until
                        ? new Date(tn.paid_until).toLocaleDateString("ru-RU")
                        : "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={tn.whatsapp_connected ? "default" : "secondary"}>
                        {tn.whatsapp_connected ? t("st_wa_connected") : "—"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="sm" onClick={() => loginAsTenant(tn.id).then(() => router.push("/dashboard"))}>
                          <SignIn className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => { setExtendTenant(tn); setExtendMonths(1); }}>
                          <CalendarPlus className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => { setTgTenant(tn); setTgCode(""); }}>
                          <Key className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => { setCredsTenant(tn); setCreds({ phone_number_id: "", access_token: "", app_secret: "", verify_token: "", business_name: "" }); setTestWa(""); }}>
                          <WhatsappLogo className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" className="text-destructive" onClick={() => { if (confirm(t("ad_confirm_delete").replace("{name}", tn.name))) delMut.mutate(tn.id); }}>
                          <Trash className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* ADD CLIENT */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("ad_add_client")}</DialogTitle>
            <DialogDescription>20 000 ₸ / {lang === "kz" ? "ай" : "месяц"}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>{t("ad_name")}</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Slug</Label>
                <Input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} placeholder="my-beauty" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>{t("ad_email")}</Label>
                <Input type="email" value={form.login_email} onChange={(e) => setForm({ ...form, login_email: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>{t("ad_password")}</Label>
                <Input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label>{t("ad_contact")}</Label>
                <Input value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>{t("ad_months")}</Label>
                <Input type="number" value={form.months_paid} onChange={(e) => setForm({ ...form, months_paid: Number(e.target.value) })} />
              </div>
              <div className="space-y-2">
                <Label>{t("ad_sub_price")}</Label>
                <Input type="number" value={form.subscription_price} onChange={(e) => setForm({ ...form, subscription_price: Number(e.target.value) })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>{t("cancel")}</Button>
            <Button onClick={() => createMut.mutate()} disabled={!form.name || !form.slug || createMut.isPending}>
              {t("save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* EXTEND */}
      <Dialog open={!!extendTenant} onOpenChange={(o) => !o && setExtendTenant(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("ad_extend")} — {extendTenant?.name}</DialogTitle>
          </DialogHeader>
          <div className="flex items-end gap-3">
            <div className="space-y-2 flex-1">
              <Label>{t("ad_extend_months")}</Label>
              <Input type="number" value={extendMonths} onChange={(e) => setExtendMonths(Number(e.target.value))} />
            </div>
            <Button onClick={() => extendMut.mutate()} disabled={extendMut.isPending}>
              {t("save")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* TG CODE */}
      <Dialog open={!!tgTenant} onOpenChange={(o) => !o && setTgTenant(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("ad_tg_code")} — {tgTenant?.name}</DialogTitle>
          </DialogHeader>
          {tgCode ? (
            <div className="rounded-xl border-2 border-dashed border-primary p-6 text-center">
              <p className="text-5xl font-extrabold tracking-[0.3em] text-primary">{tgCode}</p>
              <Button variant="outline" size="sm" className="mt-4 gap-2" onClick={copyCode}>
                <Copy className="h-4 w-4" /> {t("save")}
              </Button>
            </div>
          ) : (
            <Button onClick={() => tgCodeMut.mutate()} disabled={tgCodeMut.isPending}>
              <Key className="mr-2 h-4 w-4" /> {t("st_tg_code_btn")}
            </Button>
          )}
        </DialogContent>
      </Dialog>

      {/* WA CREDS WIZARD */}
      <Dialog open={!!credsTenant} onOpenChange={(o) => !o && setCredsTenant(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              <WhatsappLogo weight="duotone" className="mr-1 inline h-5 w-5 text-primary" />
              {t("ad_wa_creds")} — {credsTenant?.name}
            </DialogTitle>
            <DialogDescription>
              {t("ad_wa_steps").replace(
                "{url}",
                "https://danyshpan.xyz/webhook"
              )}
            </DialogDescription>
          </DialogHeader>
          <Separator />
          <div className="grid gap-4">
            <div className="space-y-2">
              <Label>{t("ad_wa_phone_id")}</Label>
              <Input value={creds.phone_number_id} onChange={(e) => setCreds({ ...creds, phone_number_id: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("ad_wa_token")}</Label>
              <Input type="password" value={creds.access_token} onChange={(e) => setCreds({ ...creds, access_token: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("ad_wa_secret")}</Label>
              <Input type="password" value={creds.app_secret} onChange={(e) => setCreds({ ...creds, app_secret: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("ad_wa_verify")}</Label>
              <Input value={creds.verify_token} onChange={(e) => setCreds({ ...creds, verify_token: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>{t("ad_wa_biz")}</Label>
              <Input value={creds.business_name} onChange={(e) => setCreds({ ...creds, business_name: e.target.value })} />
            </div>
            <Button onClick={() => credsMut.mutate()} disabled={!creds.phone_number_id || !creds.access_token}>
              {t("ad_wa_save")}
            </Button>
            <Separator />
            <div className="space-y-2">
              <Label>{t("ad_wa_test")}</Label>
              <div className="flex gap-2">
                <Input value={testWa} onChange={(e) => setTestWa(e.target.value)} placeholder="+77070000000" />
                <Button variant="outline" onClick={() => testMut.mutate()} disabled={!testWa || testMut.isPending}>
                  <PaperPlaneTilt className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
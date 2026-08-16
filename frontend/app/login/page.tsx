"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { WhatsappLogo, SignIn, WarningCircle, Translate } from "@phosphor-icons/react";
import { ApiError } from "@/lib/api";
import Link from "next/link";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function LoginPage() {
  const { login } = useAuth();
  const { t, lang, setLang } = useI18n();
  const router = useRouter();
  const [tab, setTab] = useState<"tenant" | "admin">("tenant");
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(tab, a, b);
      router.push(tab === "admin" ? "/admin" : "/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? t("login_error") : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-emerald-50 to-white px-4 dark:from-background dark:to-background">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3">
          <Link href="/">
            <div className="flex items-center gap-2">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
                <WhatsappLogo weight="duotone" className="h-6 w-6" />
              </div>
              <span className="text-2xl font-bold tracking-tight">Angime</span>
            </div>
          </Link>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground">
                <Translate className="h-4 w-4" /> {lang === "ru" ? "Русский" : "Қазақша"}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="center">
              <DropdownMenuItem onClick={() => setLang("ru")}>{t("lang_ru")}</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setLang("kz")}>{t("lang_kz")}</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <Card className="shadow-xl">
          <CardHeader>
            <CardTitle className="text-xl">{t("login_title")}</CardTitle>
            <CardDescription>
              {tab === "admin" ? t("login_admin") : t("login_tenant")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={tab} onValueChange={(v) => setTab(v as "tenant" | "admin")}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="tenant">{t("login_tenant")}</TabsTrigger>
                <TabsTrigger value="admin">{t("login_admin")}</TabsTrigger>
              </TabsList>
              <TabsContent value="tenant">
                <form onSubmit={submit} className="mt-4 space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">{t("login_email")}</Label>
                    <Input
                      id="email"
                      type="email"
                      value={a}
                      onChange={(e) => setA(e.target.value)}
                      placeholder="owner@business.kz"
                      required
                      autoComplete="email"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="pass">{t("login_password")}</Label>
                    <Input
                      id="pass"
                      type="password"
                      value={b}
                      onChange={(e) => setB(e.target.value)}
                      required
                      autoComplete="current-password"
                    />
                  </div>
                  {error && (
                    <Alert variant="destructive">
                      <WarningCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}
                  <Button type="submit" className="w-full gap-2" disabled={loading}>
                    <SignIn className="h-4 w-4" />
                    {loading ? t("login_loading") : t("login_button")}
                  </Button>
                </form>
              </TabsContent>
              <TabsContent value="admin">
                <form onSubmit={submit} className="mt-4 space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="username">{t("login_username")}</Label>
                    <Input
                      id="username"
                      value={a}
                      onChange={(e) => setA(e.target.value)}
                      required
                      autoComplete="username"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="apass">{t("login_password")}</Label>
                    <Input
                      id="apass"
                      type="password"
                      value={b}
                      onChange={(e) => setB(e.target.value)}
                      required
                      autoComplete="current-password"
                    />
                  </div>
                  {error && (
                    <Alert variant="destructive">
                      <WarningCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}
                  <Button type="submit" className="w-full gap-2" disabled={loading}>
                    <SignIn className="h-4 w-4" />
                    {loading ? t("login_loading") : t("login_button")}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
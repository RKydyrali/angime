"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarFooter,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Gauge,
  Stack,
  CalendarCheck,
  GearSix,
  ShieldCheck,
  SignOut,
  WhatsappLogo,
  Translate,
} from "@phosphor-icons/react";

function NavItems() {
  const { t } = useI18n();
  const { auth } = useAuth();
  const pathname = usePathname();

  const items = [
    { href: "/dashboard", icon: Gauge, label: t("nav_dashboard") },
    { href: "/services", icon: Stack, label: t("nav_services") },
    { href: "/bookings", icon: CalendarCheck, label: t("nav_bookings") },
    { href: "/settings", icon: GearSix, label: t("nav_settings") },
  ];
  if (auth.role === "admin") {
    items.push({ href: "/admin", icon: ShieldCheck, label: t("nav_admin") });
  }

  return (
    <>
      {items.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <SidebarMenuItem key={item.href}>
            <SidebarMenuButton asChild isActive={active} tooltip={item.label}>
              <Link href={item.href}>
                <item.icon weight={active ? "fill" : "duotone"} className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        );
      })}
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const { auth, logout } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!auth.token) {
      router.replace("/login");
    }
  }, [auth.token, router]);

  if (!auth.token) {
    return null;
  }

  const doLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <SidebarProvider>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <Link href="/" className="flex items-center gap-2 px-2 py-1">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
              <WhatsappLogo weight="duotone" className="h-4 w-4" />
            </div>
            <span className="text-lg font-bold tracking-tight text-sidebar-foreground">
              Angime
            </span>
          </Link>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>{auth.role === "admin" ? t("nav_admin") : auth.name || "Panel"}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <NavItems />
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuButton>
                    <Translate className="h-4 w-4" />
                    <span>{lang === "ru" ? t("lang_ru") : t("lang_kz")}</span>
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent side="top" align="start">
                  <DropdownMenuItem onClick={() => setLang("ru")}>
                    {t("lang_ru")}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setLang("kz")}>
                    {t("lang_kz")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton onClick={doLogout}>
                <SignOut className="h-4 w-4" />
                <span>{t("nav_logout")}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <span className="text-sm font-medium text-muted-foreground">
            {auth.name || t("app_name")}
          </span>
          <div className="ml-auto flex items-center gap-2">
            {auth.role === "admin" ? (
              <Button variant="ghost" size="sm" asChild>
                <Link href="/admin">
                  <ShieldCheck className="mr-1 h-4 w-4" /> {t("nav_admin")}
                </Link>
              </Button>
            ) : null}
          </div>
        </header>
        <main className="p-4 md:p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
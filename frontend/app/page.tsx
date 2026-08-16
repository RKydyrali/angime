"use client";

import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ChatCircleText,
  CalendarCheck,
  BellRinging,
  ChartBar,
  WhatsappLogo,
  Translate,
  ArrowRight,
  PaperPlaneTilt,
} from "@phosphor-icons/react";
import Link from "next/link";

const FEATURES: Array<{ icon: React.ElementType; title: TKey; desc: TKey }> = [
  { icon: CalendarCheck, title: "f1_title", desc: "f1_desc" },
  { icon: ChatCircleText, title: "f2_title", desc: "f2_desc" },
  { icon: BellRinging, title: "f3_title", desc: "f3_desc" },
  { icon: ChartBar, title: "f4_title", desc: "f4_desc" },
];

const STEPS: Array<{ title: TKey; desc: TKey }> = [
  { title: "h1", desc: "h1_desc" },
  { title: "h2", desc: "h2_desc" },
  { title: "h3", desc: "h3_desc" },
];

type TKey = Parameters<ReturnType<typeof useI18n>["t"]>[0];

export default function Landing() {
  const { t, lang, setLang } = useI18n();

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50 via-white to-white dark:from-background dark:via-background dark:to-background">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <WhatsappLogo weight="duotone" className="h-5 w-5" />
          </div>
          <span className="text-xl font-bold tracking-tight">Angime</span>
        </div>
        <div className="flex items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2">
                <Translate className="h-4 w-4" />
                {lang === "ru" ? "Русский" : "Қазақша"}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setLang("ru")}>
                {t("lang_ru")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setLang("kz")}>
                {t("lang_kz")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Link href="/login">
            <Button size="sm">{t("hero_cta")}</Button>
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-20 pt-16 text-center">
        <span className="inline-flex items-center gap-2 rounded-full border bg-white px-4 py-1.5 text-sm font-medium text-emerald-700 shadow-sm dark:bg-card dark:text-emerald-400">
          <WhatsappLogo weight="duotone" className="h-4 w-4" />
          {t("hero_badge")}
        </span>
        <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl md:text-6xl">
          {t("hero_title")}
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          {t("hero_subtitle")}
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link href="/login">
            <Button size="lg" className="gap-2">
              {t("hero_cta")} <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-14">
        <h2 className="text-center text-3xl font-bold tracking-tight">
          {t("features_title")}
        </h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border bg-white p-6 shadow-sm transition hover:shadow-md dark:bg-card"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <f.icon weight="duotone" className="h-6 w-6" />
              </div>
              <h3 className="mt-4 font-semibold">{t(f.title)}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{t(f.desc)}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-14">
        <h2 className="text-center text-3xl font-bold tracking-tight">
          {t("how_title")}
        </h2>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <div
              key={i}
              className="relative rounded-2xl border bg-white p-6 shadow-sm dark:bg-card"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                {i + 1}
              </div>
              <h3 className="mt-4 font-semibold">{t(s.title)}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{t(s.desc)}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="rounded-3xl bg-gradient-to-br from-emerald-600 to-teal-700 p-10 text-center text-white shadow-xl">
          <h2 className="text-2xl font-bold sm:text-3xl">{t("price_title")}</h2>
          <div className="mt-4 flex items-end justify-center gap-2">
            <span className="text-5xl font-extrabold">{t("price_amount")}</span>
            <span className="pb-1.5 text-lg text-emerald-100">{t("price_per")}</span>
          </div>
          <p className="mx-auto mt-4 max-w-md text-emerald-100">{t("price_desc")}</p>
          <Link href="/login">
            <Button
              size="lg"
              className="mt-8 gap-2 bg-white text-emerald-700 hover:bg-emerald-50"
            >
              {t("hero_cta")} <PaperPlaneTilt className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        © {new Date().getFullYear()} Angime — {t("cta_desc")}
      </footer>
    </div>
  );
}
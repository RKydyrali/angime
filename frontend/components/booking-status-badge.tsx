"use client";

import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/lib/i18n";

const STYLES: Record<string, string> = {
  confirmed: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/40 dark:text-emerald-300",
  cancelled: "bg-red-100 text-red-700 hover:bg-red-100 dark:bg-red-900/40 dark:text-red-300",
  completed: "bg-sky-100 text-sky-700 hover:bg-sky-100 dark:bg-sky-900/40 dark:text-sky-300",
  no_show: "bg-zinc-200 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300",
};

export function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  const label: Record<string, string> = {
    confirmed: t("bk_status_confirmed"),
    cancelled: t("bk_status_cancelled"),
    completed: t("bk_status_completed"),
    no_show: t("bk_status_no_show"),
  };
  return (
    <Badge variant="outline" className={STYLES[status] || ""}>
      {label[status] || status}
    </Badge>
  );
}
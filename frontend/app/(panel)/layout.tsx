"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";

export default function PanelLayout({ children }: { children: React.ReactNode }) {
  const { auth, ready } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (ready && auth.role === "admin" && !pathname.startsWith("/admin")) {
      router.replace("/admin");
    }
  }, [ready, auth.role, pathname, router]);

  return <AppShell>{children}</AppShell>;
}
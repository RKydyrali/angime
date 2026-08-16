"use client";

import React from "react";
import { QueryClient, QueryClientProvider as QC } from "@tanstack/react-query";
import { AuthProvider } from "@/lib/auth";
import { I18nProvider } from "@/lib/i18n";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

export function QueryClientProvider({ children }: { children: React.ReactNode }) {
  return (
    <QC client={queryClient}>
      <AuthProvider>
        <I18nProvider>{children}</I18nProvider>
      </AuthProvider>
    </QC>
  );
}
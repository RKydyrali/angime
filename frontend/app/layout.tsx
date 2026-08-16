import type { Metadata } from "next";
import localFont from "next/font/local";
import { QueryClientProvider } from "./providers";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Angime — WhatsApp-бот для записей",
  description:
    "Мультитенантный WhatsApp-бот: записи, FAQ, напоминания и панель управления.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className={`${geistSans.variable} antialiased`}>
        <QueryClientProvider>
          {children}
          <Toaster richColors position="top-right" />
        </QueryClientProvider>
      </body>
    </html>
  );
}
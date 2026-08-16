"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
} from "@/components/ui/sheet";
import { ChatCircleDots, PaperPlaneTilt, SpinnerGap } from "@phosphor-icons/react";

interface Msg {
  role: "user" | "assistant";
  text: string;
}

export function AiChat() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setLoading(true);
    setError("");
    try {
      const res = await api<{ reply: string }>("/api/tenant/ai-chat", {
        method: "POST",
        body: { question: text },
      });
      setMessages((m) => [...m, { role: "assistant", text: res.reply }]);
    } catch {
      setError(t("dash_ai_error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button className="fixed bottom-5 right-5 z-50 h-14 w-14 rounded-full shadow-lg">
          <ChatCircleDots weight="fill" className="h-6 w-6" />
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-md">
        <SheetHeader className="border-b p-4">
          <SheetTitle className="flex items-center gap-2">
            <ChatCircleDots weight="duotone" className="h-5 w-5 text-primary" />
            {t("nav_dashboard")}
          </SheetTitle>
          <p className="text-xs text-muted-foreground">{t("dash_ai_hint")}</p>
        </SheetHeader>
        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
          {messages.length === 0 && !loading && (
            <p className="rounded-2xl bg-muted p-4 text-sm text-muted-foreground">
              {t("dash_ai_welcome")}
            </p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user"
                  ? "ml-auto bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
            >
              {m.text}
            </div>
          ))}
          {loading && (
            <div className="flex w-fit items-center gap-2 rounded-2xl bg-muted px-4 py-2.5 text-sm text-muted-foreground">
              <SpinnerGap className="h-4 w-4 animate-spin" />
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <SheetFooter className="border-t p-3">
          <form
            className="flex w-full gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t("dash_ai_placeholder")}
              className="flex-1"
            />
            <Button type="submit" size="icon" disabled={loading || !input.trim()}>
              <PaperPlaneTilt className="h-4 w-4" />
            </Button>
          </form>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
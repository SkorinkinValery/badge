"use client";

import { ReactNode, useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as RToast from "@radix-ui/react-toast";
import { Button, PixelH } from "./primitives";

/* ---------- Modal (Radix Dialog) ---------- */
export function Modal({
  open,
  onClose,
  title = "Диалог",
  w = 460,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  w?: number;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          className="fixed inset-0 z-[200]"
          style={{ background: "rgba(0,0,0,.72)", backdropFilter: "blur(2px)" }}
        />
        <Dialog.Content
          onOpenAutoFocus={(e) => e.preventDefault()}
          className="fixed left-1/2 top-1/2 z-[200] -translate-x-1/2 -translate-y-1/2 border border-border-2 bg-surface"
          style={{ width: w, maxWidth: "calc(100vw - 40px)" }}
        >
          <Dialog.Title className="sr-only">{title}</Dialog.Title>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirmText = "Подтвердить",
  danger,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmText?: string;
  danger?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal open={open} onClose={onClose} title={title} w={440}>
      <div className="px-6 pb-[22px] pt-6">
        <PixelH size={22}>{title}</PixelH>
        <p className="mt-3 text-[13.5px] text-muted">{body}</p>
        <div className="mt-6 flex justify-end gap-[10px]">
          <Button variant="ghost" sm onClick={onClose}>
            Отмена
          </Button>
          <Button
            variant={danger ? "danger" : "solid"}
            sm
            onClick={() => {
              onConfirm();
              onClose();
            }}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

/* ---------- Toast system (Radix Toast + global dispatch) ---------- */
type ToastKind = "success" | "error" | "info";
interface ToastItem {
  id: number;
  msg: string;
  kind: ToastKind;
}

const TOAST_EVENT = "app-toast";

export function toast(msg: string, kind: ToastKind = "success") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<ToastItem>(TOAST_EVENT, {
      detail: { msg, kind, id: Date.now() + Math.random() },
    }),
  );
}

const TOAST_COLOR: Record<ToastKind, string> = {
  success: "var(--success)",
  error: "var(--danger)",
  info: "var(--accent)",
};

export function Toaster() {
  const [items, setItems] = useState<ToastItem[]>([]);
  useEffect(() => {
    const h = (e: Event) => {
      const t = (e as CustomEvent<ToastItem>).detail;
      setItems((x) => [...x, t]);
      setTimeout(() => setItems((x) => x.filter((i) => i.id !== t.id)), 3200);
    };
    window.addEventListener(TOAST_EVENT, h);
    return () => window.removeEventListener(TOAST_EVENT, h);
  }, []);

  return (
    <RToast.Provider duration={3200} swipeDirection="right">
      {items.map((t) => (
        <RToast.Root
          key={t.id}
          className="flex items-center gap-[11px] border border-border-2 bg-surface-2 px-4 py-3"
          style={{
            borderLeft: `3px solid ${TOAST_COLOR[t.kind]}`,
            minWidth: 240,
            maxWidth: 340,
            animation: "toastin .22s ease",
            boxShadow: "0 8px 30px rgba(0,0,0,.5)",
          }}
        >
          <span style={{ width: 8, height: 8, background: TOAST_COLOR[t.kind], flex: "none" }} />
          <RToast.Description className="text-[13px]">{t.msg}</RToast.Description>
        </RToast.Root>
      ))}
      <RToast.Viewport className="fixed bottom-5 right-5 z-[300] flex flex-col gap-[10px] outline-none" />
    </RToast.Provider>
  );
}

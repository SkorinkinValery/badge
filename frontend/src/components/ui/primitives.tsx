"use client";

import { ButtonHTMLAttributes, ReactNode } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/cn";

/* ---------- Button (Btn) ---------- */
type Variant = "solid" | "light" | "ghost" | "dark" | "danger";

const VARIANT: Record<Variant, string> = {
  solid: "bg-accent text-black font-semibold hover:bg-[#ff6a30] border-transparent",
  light: "bg-white text-black font-semibold hover:bg-[#eee] border-transparent",
  ghost: "text-text border-border-2 hover:border-accent hover:text-accent",
  dark: "bg-black text-white border-black hover:bg-[#1a1a1a]",
  danger: "text-danger border-danger/40 hover:bg-danger/[0.12]",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  sm?: boolean;
  full?: boolean;
  asChild?: boolean;
}

export function Button({
  variant = "solid",
  sm,
  full,
  asChild,
  className,
  type,
  children,
  ...rest
}: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      type={asChild ? undefined : type || "button"}
      className={cn(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-sm border font-sans font-medium tracking-[.02em] transition-colors",
        "disabled:pointer-events-none disabled:opacity-45",
        sm ? "px-3.5 py-[7px] text-xs" : "px-5 py-[11px] text-[13px]",
        full && "w-full",
        VARIANT[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </Comp>
  );
}

/* ---------- Form field + input class ---------- */
export const inputClass =
  "w-full rounded-sm border border-border-2 bg-surface-2 px-[13px] py-[11px] text-[13.5px] text-text font-sans outline-none focus:border-accent placeholder:text-muted-2";

export function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-[7px]">
      <span className="mono text-[10.5px] uppercase tracking-[.1em] text-muted">
        {label}
        {required && <span className="text-accent"> *</span>}
      </span>
      {children}
      {hint && <span className="text-[11.5px] text-muted-2">{hint}</span>}
    </label>
  );
}

/* ---------- Pixel heading + kicker ---------- */
export function PixelH({
  children,
  size = 30,
  className,
}: {
  children: ReactNode;
  size?: number;
  className?: string;
}) {
  return (
    <h2 className={cn("disp", className)} style={{ fontSize: size }}>
      {children}
    </h2>
  );
}

export function Kicker({ children }: { children: ReactNode }) {
  return (
    <div className="mono flex items-center gap-[9px] text-[11px] uppercase tracking-[.12em] text-accent">
      <span className="sq" />
      {children}
    </div>
  );
}

/* ---------- Skeleton ---------- */
export function Skeleton({
  h = 16,
  w = "100%",
  className,
}: {
  h?: number | string;
  w?: number | string;
  className?: string;
}) {
  return <div className={cn("sk", className)} style={{ height: h, width: w }} />;
}

/* ---------- Delta (▲/▼ %) ---------- */
export function Delta({ v, suffix = "%" }: { v: number; suffix?: string }) {
  const up = v >= 0;
  return (
    <span
      className="mono text-[11px] font-bold"
      style={{ color: up ? "var(--success)" : "var(--danger)" }}
    >
      {up ? "▲" : "▼"} {Math.abs(v)}
      {suffix}
    </span>
  );
}

/* ---------- Panel (bordered section with optional header) ---------- */
export function Panel({
  title,
  right,
  pad = 22,
  className,
  children,
}: {
  title?: ReactNode;
  right?: ReactNode;
  pad?: number;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("border border-border bg-bg", className)}>
      {(title || right) && (
        <div className="flex items-center justify-between gap-3 border-b border-border px-[18px] py-[14px]">
          <span className="mono text-[11.5px] uppercase tracking-[.08em] text-muted">{title}</span>
          {right}
        </div>
      )}
      <div style={{ padding: pad }}>{children}</div>
    </div>
  );
}

/* ---------- Hex logo + concentric motif ---------- */
function hexPoints(cx: number, cy: number, r: number): string {
  const a: string[] = [];
  for (let i = 0; i < 6; i++) {
    const ang = (Math.PI / 180) * (60 * i - 30);
    a.push(`${(cx + r * Math.cos(ang)).toFixed(2)},${(cy + r * Math.sin(ang)).toFixed(2)}`);
  }
  return a.join(" ");
}

export function HexLogo({
  size = 22,
  stroke = "var(--text)",
  fill = "var(--accent)",
}: {
  size?: number;
  stroke?: string;
  fill?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      style={{ display: "block", shapeRendering: "crispEdges" }}
    >
      <polygon points={hexPoints(10, 10, 9)} fill="none" stroke={stroke} strokeWidth="1.4" />
      <polygon points={hexPoints(10, 10, 4.6)} fill={fill} />
    </svg>
  );
}

export function HexMotif({ size = 120 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      style={{ display: "block", shapeRendering: "crispEdges" }}
    >
      {[54, 40, 26].map((r, i) => (
        <polygon
          key={r}
          points={hexPoints(60, 60, r)}
          fill="none"
          stroke={i === 2 ? "var(--accent)" : "var(--border-2)"}
          strokeWidth={i === 2 ? 2 : 1.5}
          strokeDasharray={i === 1 ? "3 4" : undefined}
        />
      ))}
      <polygon points={hexPoints(60, 60, 11)} fill="var(--accent)" />
    </svg>
  );
}

"use client";

import { Fragment, ReactNode } from "react";
import Link from "next/link";
import { Kicker, PixelH } from "@/components/ui";

export interface Crumb {
  label: string;
  href?: string;
}

export function Page({
  title,
  kicker,
  actions,
  crumb,
  wide,
  children,
}: {
  title: ReactNode;
  kicker?: ReactNode;
  actions?: ReactNode;
  crumb?: Crumb[];
  wide?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className="mx-auto px-8 pb-20 pt-[30px]"
      style={{ maxWidth: wide ? 1320 : 1120 }}
    >
      {crumb && (
        <div className="mono mb-4 flex items-center gap-2 text-[11.5px] text-muted">
          {crumb.map((c, i) => (
            <Fragment key={i}>
              {i > 0 && <span className="text-muted-2">/</span>}
              {c.href ? (
                <Link href={c.href} className="text-muted transition-colors hover:text-accent">
                  {c.label}
                </Link>
              ) : (
                <span className="text-text">{c.label}</span>
              )}
            </Fragment>
          ))}
        </div>
      )}
      <div className="mb-7 flex flex-wrap items-end justify-between gap-5">
        <div>
          {kicker && (
            <div className="mb-[14px]">
              <Kicker>{kicker}</Kicker>
            </div>
          )}
          <PixelH size={38}>{title}</PixelH>
        </div>
        {actions && <div className="flex flex-wrap gap-[10px]">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

"use client";

/* HydraDB-style charts, hand-rolled SVG (ported from design/charts.jsx). */

export interface KpiBar {
  label: string;
  v: number;
}

export function KpiBars({ data, height = 210 }: { data: KpiBar[]; height?: number }) {
  const max = 100;
  return (
    <div className="flex flex-col">
      <div
        className="flex items-end gap-[18px] border-b border-l border-border px-1"
        style={{ height }}
      >
        {data.map((d, i) => (
          <div
            key={i}
            className="flex h-full flex-1 flex-col items-center justify-end gap-2"
          >
            <span
              className="num text-[15px]"
              style={{ color: d.v < 60 ? "var(--neutral)" : "var(--text)" }}
            >
              {d.v}
            </span>
            <div
              className="relative w-full"
              style={{
                maxWidth: 54,
                height: `${(d.v / max) * (height - 40)}px`,
                background: d.v < 60 ? "var(--neutral)" : "var(--accent)",
              }}
            >
              <div
                className="absolute inset-0"
                style={{
                  backgroundImage:
                    "repeating-linear-gradient(0deg,rgba(0,0,0,.18) 0,rgba(0,0,0,.18) 1px,transparent 1px,transparent 5px)",
                }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-[18px] px-1 pt-[10px]">
        {data.map((d, i) => (
          <span
            key={i}
            className="mono flex-1 text-center text-[10px] tracking-[.02em] text-muted"
          >
            {d.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function TrendLine({
  data,
  labels,
  height = 230,
  target = 70,
}: {
  data: number[];
  labels: string[];
  height?: number;
  target?: number;
}) {
  const W = 720;
  const H = height;
  const padL = 40;
  const padR = 16;
  const padT = 20;
  const padB = 30;
  const min = 40;
  const max = 100;
  const xs = (i: number) => padL + (i / (data.length - 1)) * (W - padL - padR);
  const ys = (v: number) => padT + (1 - (v - min) / (max - min)) * (H - padT - padB);
  const line = data.map((v, i) => `${xs(i)},${ys(v)}`).join(" ");
  const area =
    `M${xs(0)},${ys(data[0])} ` +
    data.map((v, i) => `L${xs(i)},${ys(v)}`).join(" ") +
    ` L${xs(data.length - 1)},${H - padB} L${xs(0)},${H - padB} Z`;
  const yticks = [40, 60, 80, 100];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", display: "block" }} preserveAspectRatio="none">
      <defs>
        <linearGradient id="trendfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(255,90,31,.42)" />
          <stop offset="100%" stopColor="rgba(255,90,31,.02)" />
        </linearGradient>
      </defs>
      {yticks.map((t) => (
        <g key={t}>
          <line x1={padL} y1={ys(t)} x2={W - padR} y2={ys(t)} stroke="var(--border)" strokeWidth="1" />
          <text
            x={padL - 8}
            y={ys(t) + 3}
            textAnchor="end"
            fontFamily="var(--font-mono)"
            fontSize="9"
            fill="var(--muted-2)"
          >
            {t}
          </text>
        </g>
      ))}
      <line
        x1={padL}
        y1={ys(target)}
        x2={W - padR}
        y2={ys(target)}
        stroke="var(--accent-2)"
        strokeWidth="1"
        strokeDasharray="4 4"
        opacity=".5"
      />
      <text
        x={W - padR}
        y={ys(target) - 5}
        textAnchor="end"
        fontFamily="var(--font-mono)"
        fontSize="9"
        fill="var(--accent-2)"
      >
        цель {target}
      </text>
      <path d={area} fill="url(#trendfill)" />
      <polyline points={line} fill="none" stroke="var(--accent)" strokeWidth="2.5" />
      {data.map((v, i) => (
        <rect key={i} x={xs(i) - 2.5} y={ys(v) - 2.5} width="5" height="5" fill="#fff" />
      ))}
      {labels.map((l, i) =>
        l ? (
          <text
            key={i}
            x={xs(i)}
            y={H - 10}
            textAnchor="middle"
            fontFamily="var(--font-mono)"
            fontSize="9"
            fill="var(--muted)"
          >
            {l}
          </text>
        ) : null,
      )}
    </svg>
  );
}

export function Legend({ items }: { items: { c: string; l: string }[] }) {
  return (
    <div className="flex flex-wrap gap-5">
      {items.map((it, i) => (
        <div key={i} className="mono flex items-center gap-2 text-[11px] text-muted">
          <span style={{ width: 11, height: 11, background: it.c, flex: "none" }} />
          {it.l}
        </div>
      ))}
    </div>
  );
}

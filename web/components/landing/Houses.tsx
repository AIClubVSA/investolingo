"use client";

import AnimatedContent from "../reactbits/AnimatedContent";
import { TICKERS } from "@/lib/game";

const OPENING: Record<string, number> = {
  IRON: 184.0, EMBR: 276.4, FRGE: 231.5, VRDT: 77.2, LEAF: 312.8,
  SAIL: 167.3, BANK: 204.0, AEGS: 158.9, GATE: 341.0, WYRM: 125.3,
};

const STRATEGIES = ["expand", "defend", "innovate"] as const;

/**
 * The listings table. Rows enter in sequence on scroll — a board being posted,
 * one line at a time — rather than all fading in together.
 */
export function Houses() {
  return (
    <section className="border-b border-line bg-ink-900 py-24">
      <div className="mx-auto max-w-6xl px-5">
        <div className="mb-3 flex items-center gap-3">
          <span className="h-px w-10 bg-brass-dim" aria-hidden />
          <p className="eyebrow">The listings</p>
        </div>
        <h2 className="mb-10 max-w-2xl font-display text-3xl leading-tight text-text sm:text-4xl">
          Ten chartered houses, each with a balance sheet that answers back.
        </h2>

        <div className="border border-line bg-ink-800">
          {/* Header row */}
          <div className="hidden grid-cols-[5rem_minmax(0,1fr)_8rem_7rem_7rem] border-b border-line px-4 py-2.5 sm:grid">
            {["Symbol", "House", "Sector", "Output", "Open"].map((h, i) => (
              <div
                key={h}
                className={`eyebrow ${i === 4 ? "text-right" : ""}`}
              >
                {h}
              </div>
            ))}
          </div>

          {TICKERS.map((t, i) => (
            <AnimatedContent
              key={t.symbol}
              distance={26}
              direction="vertical"
              duration={0.5}
              ease="power2.out"
              initialOpacity={0}
              threshold={0.05}
              delay={i * 0.04}
            >
              <div className="group grid grid-cols-[4.5rem_minmax(0,1fr)_auto] items-baseline gap-x-3 border-b border-line px-4 py-3 transition-colors duration-200 last:border-b-0 hover:bg-ink-700 sm:grid-cols-[5rem_minmax(0,1fr)_8rem_7rem_7rem] sm:gap-x-0">
                <div className="font-mono text-sm font-semibold tracking-wider text-brass">
                  {t.symbol}
                </div>
                <div className="font-display text-[15px] text-text">
                  {t.house}
                </div>
                <div className="hidden text-[13px] text-muted sm:block">
                  {t.sector}
                </div>
                <div className="hidden text-[13px] text-faint sm:block">
                  {t.output}
                </div>
                <div className="tabular text-right text-sm text-text">
                  {OPENING[t.symbol].toFixed(2)}
                </div>
              </div>
            </AnimatedContent>
          ))}
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {STRATEGIES.map((s, i) => (
            <AnimatedContent
              key={s}
              distance={20}
              duration={0.5}
              ease="power2.out"
              initialOpacity={0}
              threshold={0.1}
              delay={i * 0.08}
            >
              <div className="h-full border border-line bg-ink-800 p-5">
                <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.16em] text-brass">
                  {s}
                </div>
                <p className="text-[14px] leading-relaxed text-muted">
                  {s === "expand" &&
                    "Leverages the balance sheet for growth. Debt compounds quietly, and a shock lands hardest here."}
                  {s === "defend" &&
                    "Accumulates cash and waits. Slow in a rally, but the last house standing through a credit crunch."}
                  {s === "innovate" &&
                    "Builds inventory and takes a standing return premium. Steadier than expansion, dearer than defence."}
                </p>
              </div>
            </AnimatedContent>
          ))}
        </div>
      </div>
    </section>
  );
}

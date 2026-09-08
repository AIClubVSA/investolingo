"use client";

import ScrollVelocity from "./reactbits/ScrollVelocity";
import { TICKERS } from "@/lib/game";

/**
 * A tape that drifts on its own and accelerates with scroll velocity — the
 * page's pulse. Prices are the simulation's opening marks, so the tape reads
 * as the same instrument the terminal trades.
 */

const OPENING: Record<string, number> = {
  IRON: 184.0,
  EMBR: 276.4,
  FRGE: 231.5,
  VRDT: 77.2,
  LEAF: 312.8,
  SAIL: 167.3,
  BANK: 204.0,
  AEGS: 158.9,
  GATE: 341.0,
  WYRM: 125.3,
};

function Row({ offset }: { offset: number }) {
  return (
    <span className="flex items-center">
      {TICKERS.map((t, i) => {
        // Deterministic pseudo-move so the tape reads as a live board without
        // implying a price the simulation has not actually produced.
        const drift = (((i * 37 + offset * 11) % 23) - 11) / 100;
        const up = drift >= 0;
        return (
          <span key={t.symbol} className="flex items-baseline gap-2 px-5">
            <span className="font-mono text-sm font-semibold tracking-wider text-text">
              {t.symbol}
            </span>
            <span className="tabular text-sm text-muted">
              {OPENING[t.symbol].toFixed(2)}
            </span>
            <span
              className={`tabular text-xs ${up ? "text-gain" : "text-loss"}`}
            >
              {up ? "▲" : "▼"} {Math.abs(drift).toFixed(2)}%
            </span>
            <span aria-hidden className="pl-5 text-line-strong">
              /
            </span>
          </span>
        );
      })}
    </span>
  );
}

export function TickerTape() {
  return (
    <div
      className="border-y border-line bg-ink-800 py-3"
      role="marquee"
      aria-label="Aether Exchange opening marks"
    >
      <ScrollVelocity
        texts={[<Row key="a" offset={0} />, <Row key="b" offset={5} />]}
        velocity={38}
        numCopies={6}
        damping={40}
        stiffness={320}
        className="select-none"
      />
    </div>
  );
}

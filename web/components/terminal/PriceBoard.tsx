"use client";

import { useEffect, useRef, useState } from "react";
import {
  TICKER_INDEX,
  TICKERS,
  money,
  percent,
  type Company,
} from "@/lib/game";

/**
 * The board. Rows flash on the tick that moved them — the one piece of colour
 * that appears without being asked for, and the reason the board feels alive
 * when a day is advanced.
 */
export function PriceBoard({
  prices,
  previous,
  companies,
  holdings,
  selected,
  onSelect,
}: {
  prices: Record<string, number>;
  previous: Record<string, number>;
  companies: Record<string, Company>;
  holdings: Record<string, number>;
  selected: string;
  onSelect: (ticker: string) => void;
}) {
  return (
    <div className="border border-line bg-ink-800">
      <div className="grid grid-cols-[4.5rem_minmax(0,1fr)_5.5rem_5rem] items-baseline gap-x-2 border-b border-line px-4 py-2.5 sm:grid-cols-[4.5rem_minmax(0,1fr)_6rem_6rem_5.5rem_5rem]">
        <div className="eyebrow">Symbol</div>
        <div className="eyebrow">House</div>
        <div className="eyebrow hidden sm:block">Strategy</div>
        <div className="eyebrow hidden text-right sm:block">Held</div>
        <div className="eyebrow text-right">Last</div>
        <div className="eyebrow text-right">Chg</div>
      </div>

      {TICKERS.map((t) => (
        <Row
          key={t.symbol}
          symbol={t.symbol}
          house={TICKER_INDEX[t.symbol].house}
          price={prices[t.symbol] ?? 0}
          prior={previous[t.symbol] ?? prices[t.symbol] ?? 0}
          company={companies[t.symbol]}
          held={holdings[t.symbol] ?? 0}
          selected={selected === t.symbol}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}

function Row({
  symbol,
  house,
  price,
  prior,
  company,
  held,
  selected,
  onSelect,
}: {
  symbol: string;
  house: string;
  price: number;
  prior: number;
  company?: Company;
  held: number;
  selected: boolean;
  onSelect: (ticker: string) => void;
}) {
  const [flash, setFlash] = useState<"gain" | "loss" | null>(null);
  const lastPrice = useRef(price);

  useEffect(() => {
    if (price === lastPrice.current) return;
    const direction = price > lastPrice.current ? "gain" : "loss";
    lastPrice.current = price;
    setFlash(direction);
    const timer = setTimeout(() => setFlash(null), 720);
    return () => clearTimeout(timer);
  }, [price]);

  const change = prior > 0 ? (price - prior) / prior : 0;
  const bankrupt = company?.bankrupt ?? false;

  return (
    <button
      type="button"
      onClick={() => onSelect(symbol)}
      aria-pressed={selected}
      aria-label={`${symbol}, ${house}, last ${money(price)}, ${
        held > 0 ? `${held} held` : "no position"
      }`}
      className={`grid w-full cursor-pointer grid-cols-[4.5rem_minmax(0,1fr)_5.5rem_5rem] items-baseline gap-x-2 border-b border-line px-4 py-2.5 text-left transition-colors duration-200 last:border-b-0 hover:bg-ink-700 sm:grid-cols-[4.5rem_minmax(0,1fr)_6rem_6rem_5.5rem_5rem] ${
        selected ? "bg-ink-700" : ""
      } ${flash === "gain" ? "flash-gain" : ""} ${
        flash === "loss" ? "flash-loss" : ""
      }`}
    >
      <div className="flex items-baseline gap-1.5">
        {selected ? (
          <span className="text-brass" aria-hidden>
            ›
          </span>
        ) : null}
        <span
          className={`font-mono text-sm font-semibold tracking-wider ${
            selected ? "text-brass" : "text-text"
          }`}
        >
          {symbol}
        </span>
      </div>

      <div className="truncate font-display text-[15px] text-text">
        {house}
        {bankrupt ? (
          <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.14em] text-loss">
            wound up
          </span>
        ) : null}
      </div>

      <div className="hidden font-mono text-[11px] uppercase tracking-[0.1em] text-faint sm:block">
        {company?.strategy ?? "—"}
      </div>

      <div
        className={`tabular hidden text-right text-sm sm:block ${
          held > 0 ? "text-text" : "text-faint"
        }`}
      >
        {held > 0 ? held : "—"}
      </div>

      <div className="tabular text-right text-sm text-text">
        {money(price)}
      </div>

      <div
        className={`tabular text-right text-[13px] ${
          change > 0 ? "text-gain" : change < 0 ? "text-loss" : "text-faint"
        }`}
      >
        {change === 0 ? "—" : percent(change)}
      </div>
    </button>
  );
}

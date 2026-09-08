"use client";

import { useState } from "react";
import { TICKER_INDEX, money } from "@/lib/game";

const FEE_RATE = 0.001;

/**
 * The order ticket. Cost, commission and resulting cash are shown before the
 * order is sent, so a rejection from the engine is the exception rather than
 * the way the player discovers the rules.
 */
export function TradeTicket({
  ticker,
  price,
  cash,
  held,
  busy,
  error,
  onSubmit,
}: {
  ticker: string;
  price: number;
  cash: number;
  held: number;
  busy: boolean;
  error: string | null;
  onSubmit: (side: "buy" | "sell", qty: number) => void;
}) {
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState(10);

  const gross = price * qty;
  const fee = gross * FEE_RATE;
  const total = side === "buy" ? gross + fee : gross - fee;
  const cashAfter = side === "buy" ? cash - total : cash + total;

  const affordable = Math.max(0, Math.floor(cash / (price * (1 + FEE_RATE))));
  const max = side === "buy" ? affordable : held;
  const invalid =
    qty <= 0 || (side === "buy" ? total > cash : qty > held);

  return (
    <div className="border border-line bg-ink-800">
      <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
        <h2 className="eyebrow">Order ticket</h2>
        <span className="tabular text-xs text-brass">{ticker}</span>
      </div>

      <div className="p-4">
        <div className="mb-4 font-display text-[15px] text-muted">
          {TICKER_INDEX[ticker]?.house}
        </div>

        {/* Side */}
        <div
          className="mb-4 grid grid-cols-2 border border-line"
          role="group"
          aria-label="Order side"
        >
          {(["buy", "sell"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSide(s)}
              aria-pressed={side === s}
              className={`cursor-pointer py-2 text-[12px] font-bold uppercase tracking-[0.14em] transition-colors duration-200 ${
                side === s
                  ? s === "buy"
                    ? "bg-gain text-ink-900"
                    : "bg-loss text-ink-900"
                  : "text-muted hover:bg-ink-700 hover:text-text"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Quantity */}
        <label
          htmlFor="qty"
          className="eyebrow mb-1.5 block"
        >
          Quantity
        </label>
        <div className="mb-1 flex">
          <input
            id="qty"
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(Math.max(0, Number(e.target.value) || 0))}
            className="tabular w-full border border-line bg-ink-900 px-3 py-2 text-sm text-text focus:border-brass-dim focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setQty(max)}
            disabled={max <= 0}
            className="cursor-pointer border border-l-0 border-line px-3 text-[11px] font-bold uppercase tracking-[0.1em] text-muted transition-colors duration-200 hover:text-brass disabled:cursor-not-allowed disabled:text-faint"
          >
            Max
          </button>
        </div>
        <p className="tabular mb-4 text-[11px] text-faint">
          {side === "buy"
            ? `${affordable} affordable at ${money(price)}`
            : `${held} held`}
        </p>

        {/* Costing */}
        <dl className="mb-4 space-y-1.5 border-y border-line py-3 text-[13px]">
          {[
            ["Consideration", money(gross)],
            ["Commission (0.10%)", money(fee)],
            [side === "buy" ? "Total cost" : "Net proceeds", money(total)],
            ["Cash after", money(cashAfter)],
          ].map(([label, value], i) => (
            <div key={label} className="flex justify-between">
              <dt className={i >= 2 ? "text-muted" : "text-faint"}>{label}</dt>
              <dd
                className={`tabular ${
                  i === 3 && cashAfter < 0 ? "text-loss" : "text-text"
                }`}
              >
                {value}
              </dd>
            </div>
          ))}
        </dl>

        {error ? (
          <p
            role="alert"
            className="mb-3 border border-loss/40 bg-loss/10 px-3 py-2 text-[13px] text-loss"
          >
            {error}
          </p>
        ) : null}

        <button
          type="button"
          disabled={busy || invalid}
          onClick={() => onSubmit(side, qty)}
          className={`w-full cursor-pointer border px-4 py-2.5 text-[12px] font-bold uppercase tracking-[0.14em] transition-colors duration-200 disabled:cursor-not-allowed disabled:border-line disabled:bg-transparent disabled:text-faint ${
            side === "buy"
              ? "border-gain bg-gain text-ink-900 hover:bg-gain/85"
              : "border-loss bg-loss text-ink-900 hover:bg-loss/85"
          }`}
        >
          {busy
            ? "Working…"
            : invalid
              ? side === "buy"
                ? "Insufficient cash"
                : "Insufficient shares"
              : `${side} ${qty} ${ticker}`}
        </button>

        <p className="mt-3 text-[11px] leading-relaxed text-faint">
          Short selling is disabled on the Aether. Orders fill at the last
          simulated mark.
        </p>
      </div>
    </div>
  );
}

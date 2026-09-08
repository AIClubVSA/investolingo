"use client";

import { useEffect } from "react";
import { Seal } from "../Seal";
import { money } from "@/lib/game";

export interface Award {
  key: number;
  id: string;
  name: string;
  reward: number;
}

/**
 * Commission notices. Styled as a slip posted to the ledger rather than a
 * confetti burst — the seal strikes in, the grant counts against your cash.
 */
export function AwardToast({
  awards,
  onDismiss,
}: {
  awards: Award[];
  onDismiss: (key: number) => void;
}) {
  return (
    <div
      className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-[19rem] flex-col gap-2"
      role="status"
      aria-live="polite"
    >
      {awards.map((award) => (
        <Notice key={award.key} award={award} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function Notice({
  award,
  onDismiss,
}: {
  award: Award;
  onDismiss: (key: number) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(award.key), 6000);
    return () => clearTimeout(timer);
  }, [award.key, onDismiss]);

  return (
    <article className="slide-in pointer-events-auto flex items-center gap-3 border border-brass-dim bg-ink-800 p-3.5">
      <Seal id={award.id} earned animate size={44} />

      <div className="min-w-0 flex-1">
        <p className="eyebrow mb-0.5 text-brass">Commission awarded</p>
        <h3 className="truncate font-display text-[15px] text-text">
          {award.name}
        </h3>
      </div>

      <div className="shrink-0 text-right">
        <div className="tabular text-sm text-gain">
          +{money(award.reward, 0)}
        </div>
      </div>

      <button
        type="button"
        onClick={() => onDismiss(award.key)}
        aria-label="Dismiss notice"
        className="shrink-0 cursor-pointer px-1 text-faint transition-colors duration-200 hover:text-text"
      >
        ×
      </button>
    </article>
  );
}

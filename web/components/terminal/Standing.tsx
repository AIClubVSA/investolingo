"use client";

import CountUp from "../reactbits/CountUp";
import { Seal } from "../Seal";
import { levelFor, money, type Mission } from "@/lib/game";

/**
 * Rank and commissions. The rank bar is 24 struck segments rather than a
 * continuous fill, so progress reads as discrete marks earned on a ledger.
 */
export function Standing({
  xp,
  missions,
  completed,
  rewards,
}: {
  xp: number;
  missions: Mission[];
  completed: string[];
  rewards: number;
}) {
  const { level, rank, progress, ceiling } = levelFor(xp);
  const segments = 24;

  return (
    <div className="border border-line bg-ink-800">
      <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
        <h2 className="eyebrow">Standing</h2>
        <span className="tabular text-xs text-faint">Level {level}</span>
      </div>

      <div className="border-b border-line p-4">
        <div className="mb-3 flex items-baseline justify-between">
          <span className="font-display text-2xl text-text">{rank}</span>
          <span className="tabular text-sm text-brass">
            <CountUp to={xp} duration={0.9} separator="," className="tabular" />
            <span className="text-faint"> xp</span>
          </span>
        </div>

        <div
          className="mb-1.5 flex gap-[3px]"
          role="progressbar"
          aria-valuenow={Math.round(progress * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Progress to level ${level + 1}`}
        >
          {Array.from({ length: segments }).map((_, i) => (
            <span
              key={i}
              className={`h-6 flex-1 transition-colors duration-300 ${
                i / segments < progress ? "bg-brass" : "bg-ink-600"
              }`}
              style={{ transitionDelay: `${i * 14}ms` }}
            />
          ))}
        </div>

        <div className="tabular flex justify-between text-[11px] text-faint">
          <span>{Math.round(progress * 100)}% to level {level + 1}</span>
          <span>{money(ceiling, 0)} xp</span>
        </div>
      </div>

      <div className="border-b border-line px-4 py-2.5">
        <h3 className="eyebrow">Commissions</h3>
      </div>

      <ul>
        {missions.map((m) => {
          const earned = completed.includes(m.id);
          return (
            <li
              key={m.id}
              className={`flex items-center gap-3 border-b border-line px-4 py-3 last:border-b-0 transition-colors duration-500 ${
                earned ? "bg-ink-700" : ""
              }`}
            >
              <Seal id={m.id} earned={earned} animate size={40} />
              <div className="min-w-0 flex-1">
                <h4 className="truncate font-display text-[15px] text-text">
                  {m.name}
                </h4>
                <p className="truncate text-[12px] text-faint">{m.goal}</p>
              </div>
              <div
                className={`tabular shrink-0 text-right text-[13px] ${
                  earned ? "text-gain" : "text-faint"
                }`}
              >
                {earned ? "✓" : money(m.reward, 0)}
              </div>
            </li>
          );
        })}
      </ul>

      <div className="flex items-baseline justify-between border-t border-line px-4 py-3">
        <span className="eyebrow">Grants received</span>
        <span className="tabular text-sm text-brass">{money(rewards, 0)}</span>
      </div>
    </div>
  );
}

"use client";

import type { MarketEvent } from "@/lib/game";

/**
 * The wire. Active shocks sit at the top with a running countdown; resolved
 * ones fall back into the log, dimmed. Sector effects are named so the player
 * can act on them rather than guess.
 */
export function EventWire({
  events,
  active,
  day,
}: {
  events: MarketEvent[];
  active: MarketEvent[];
  day: number;
}) {
  const activeIds = new Set(active.map((e) => e.id));
  const recent = [...events].reverse().slice(0, 14);

  return (
    <div className="border border-line bg-ink-800">
      <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
        <h2 className="eyebrow">The wire</h2>
        <span className="tabular text-xs text-faint">
          {active.length} active
        </span>
      </div>

      {recent.length === 0 ? (
        <p className="px-4 py-6 text-[13px] text-faint">
          The wire is quiet. Advance the day to open the market.
        </p>
      ) : (
        <ul className="max-h-[24rem] overflow-y-auto">
          {recent.map((event) => {
            const live = activeIds.has(event.id);
            const remaining = event.day + event.duration - day;

            return (
              <li
                key={event.id}
                className={`border-b border-line px-4 py-3 last:border-b-0 ${
                  live ? "" : "opacity-55"
                }`}
              >
                <div className="mb-1 flex items-baseline justify-between gap-3">
                  <h3
                    className={`font-display text-[15px] ${
                      live ? "text-text" : "text-muted"
                    }`}
                  >
                    {event.name}
                  </h3>
                  {live ? (
                    <span className="tabular shrink-0 text-[11px] text-warn">
                      <span className="tick" aria-hidden>
                        ●
                      </span>{" "}
                      {remaining}d left
                    </span>
                  ) : (
                    <span className="tabular shrink-0 text-[11px] text-faint">
                      resolved
                    </span>
                  )}
                </div>

                <div className="tabular mb-2 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-faint">
                  <span>{event.region}</span>
                  <span>day {event.day}</span>
                  <span>severity {event.severity.toFixed(2)}</span>
                </div>

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px]">
                  <span className="text-loss">
                    ▼ {event.sectors_hurt.join(", ")}
                  </span>
                  <span className="text-gain">
                    ▲ {event.sectors_helped.join(", ")}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

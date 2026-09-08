"use client";

import { useEffect, useRef, useState } from "react";
import CountUp from "../reactbits/CountUp";
import AnimatedContent from "../reactbits/AnimatedContent";
import { Seal } from "../Seal";
import { RANKS } from "@/lib/game";

/** Mirrors MISSIONS in backend/aether_backend_v4.py. */
const MISSIONS = [
  {
    id: "first_trade",
    name: "First Trade",
    goal: "Execute one trade",
    reward: 500,
  },
  {
    id: "diversified",
    name: "Diversified",
    goal: "Hold three companies",
    reward: 1500,
  },
  {
    id: "survivor",
    name: "Market Survivor",
    goal: "Advance thirty days",
    reward: 2500,
  },
];

/**
 * Demonstrates the progression system by actually running it: when the section
 * comes into view the seals are awarded in sequence and the rank bar fills, so
 * the reader sees the reward loop before they ever place a trade.
 */
export function Progression() {
  const ref = useRef<HTMLDivElement>(null);
  const [awarded, setAwarded] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || started) return;
        setStarted(true);

        if (reduced) {
          setAwarded(MISSIONS.length);
          return;
        }
        MISSIONS.forEach((_, i) => {
          setTimeout(() => setAwarded(i + 1), 700 + i * 620);
        });
      },
      { threshold: 0.35 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [started]);

  const progress = awarded / MISSIONS.length;

  return (
    <section ref={ref} className="border-b border-line bg-ink-900 py-24">
      <div className="mx-auto max-w-6xl px-5">
        <div className="mb-3 flex items-center gap-3">
          <span className="h-px w-10 bg-brass-dim" aria-hidden />
          <p className="eyebrow">Standing</p>
        </div>
        <h2 className="mb-4 max-w-2xl font-display text-3xl leading-tight text-text sm:text-4xl">
          The exchange keeps a record of what you have earned.
        </h2>
        <p className="mb-12 max-w-2xl text-[15px] leading-relaxed text-muted">
          Commissions are awarded for days held and positions justified, not for
          volume. Each one carries a cash grant and moves you along seven ranks,
          from Apprentice to Governor.
        </p>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
          {/* Commissions */}
          <div className="border border-line bg-ink-800">
            <div className="border-b border-line px-5 py-3">
              <h3 className="eyebrow">Commissions</h3>
            </div>

            <ul>
              {MISSIONS.map((m, i) => {
                const earned = i < awarded;
                return (
                  <li
                    key={m.id}
                    className={`flex items-center gap-5 border-b border-line px-5 py-5 last:border-b-0 transition-colors duration-500 ${
                      earned ? "bg-ink-700" : ""
                    }`}
                  >
                    <Seal id={m.id} earned={earned} animate size={58} />

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <h4 className="font-display text-lg text-text">
                          {m.name}
                        </h4>
                        <span
                          className={`font-mono text-[10px] uppercase tracking-[0.16em] transition-colors duration-500 ${
                            earned ? "text-brass" : "text-faint"
                          }`}
                        >
                          {earned ? "Awarded" : "Outstanding"}
                        </span>
                      </div>
                      <p className="mt-0.5 text-[14px] text-muted">{m.goal}</p>
                    </div>

                    <div className="shrink-0 text-right">
                      <div
                        className={`tabular text-lg transition-colors duration-500 ${
                          earned ? "text-gain" : "text-faint"
                        }`}
                      >
                        {earned ? (
                          <CountUp
                            to={m.reward}
                            duration={1.1}
                            separator=","
                            className="tabular"
                          />
                        ) : (
                          m.reward.toLocaleString("en-US")
                        )}
                      </div>
                      <div className="eyebrow mt-0.5">Grant</div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Rank */}
          <AnimatedContent
            distance={24}
            duration={0.6}
            ease="power2.out"
            initialOpacity={0}
            threshold={0.15}
          >
            <div className="h-full border border-line bg-ink-800 p-5">
              <h3 className="eyebrow mb-5">Rank</h3>

              <div className="mb-1 font-display text-3xl text-text">
                {RANKS[Math.min(RANKS.length - 1, awarded)]}
              </div>
              <div className="tabular mb-6 text-xs text-faint">
                Level {awarded + 1} of {RANKS.length * 2}
              </div>

              {/* Segmented rank bar — struck marks, not a filling gradient. */}
              <div
                className="mb-2 flex gap-1"
                role="progressbar"
                aria-valuenow={awarded}
                aria-valuemin={0}
                aria-valuemax={MISSIONS.length}
                aria-label="Commissions awarded"
              >
                {Array.from({ length: 24 }).map((_, i) => {
                  const filled = i / 24 < progress;
                  return (
                    <span
                      key={i}
                      className={`h-8 flex-1 transition-colors duration-300 ${
                        filled ? "bg-brass" : "bg-ink-600"
                      }`}
                      style={{ transitionDelay: `${i * 18}ms` }}
                    />
                  );
                })}
              </div>

              <div className="tabular mb-7 flex justify-between text-[11px] text-faint">
                <span>{awarded} awarded</span>
                <span>{MISSIONS.length} total</span>
              </div>

              <div className="border-t border-line pt-5">
                <div className="eyebrow mb-2">Grants received</div>
                <div className="tabular text-2xl text-brass">
                  <CountUp
                    to={MISSIONS.slice(0, awarded).reduce(
                      (sum, m) => sum + m.reward,
                      0,
                    )}
                    duration={1.2}
                    separator=","
                    className="tabular"
                  />
                </div>
              </div>

              <ol className="mt-6 space-y-1.5 border-t border-line pt-5">
                {RANKS.map((rank, i) => (
                  <li
                    key={rank}
                    className={`flex items-baseline justify-between text-[13px] transition-colors duration-300 ${
                      i <= awarded ? "text-text" : "text-faint"
                    }`}
                  >
                    <span>{rank}</span>
                    <span className="tabular text-[11px]">
                      {i <= awarded ? "·" : "—"}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          </AnimatedContent>
        </div>
      </div>
    </section>
  );
}

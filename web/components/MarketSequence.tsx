"use client";

import { useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

/**
 * The centrepiece scroll sequence. The section pins, and scroll drives a
 * price line drawing itself left-to-right while shocks land on the curve and
 * the accompanying note changes. Scroll position *is* simulated time.
 */

const STEPS = [
  {
    label: "Day 0",
    title: "Ten houses open at par",
    body:
      "Every run begins from the same book: ten chartered houses across mining, energy, freight, credit and security, each with its own balance sheet, inventory and standing strategy.",
  },
  {
    label: "Day 7",
    title: "The tape finds its drift",
    body:
      "Prices move on company profit, inflation and a bounded random walk. No single day can move a house more than fifteen percent — the market is volatile, never absurd.",
  },
  {
    label: "Day 14",
    title: "A shock makes landfall",
    body:
      "Weather, strikes, cyberattacks, credit crunches and reforms strike a named region with a severity and a duration. Some sectors are hurt. Others are quietly helped.",
  },
  {
    label: "Day 23",
    title: "Boards respond",
    body:
      "Each house acts on its own strategy — expanding on debt, defending cash, or innovating on inventory. The consequences compound while you decide what to hold.",
  },
  {
    label: "Day 30",
    title: "The ledger is ruled off",
    body:
      "Survive thirty days and the exchange recognises it. Standing on the Aether is earned in days held and positions justified, not in a single lucky trade.",
  },
];

// A deterministic curve: a rising trend, a shock crater near day 14, recovery.
const POINTS = [
  [0, 168], [40, 160], [80, 166], [120, 148], [160, 152], [200, 134],
  [240, 140], [280, 120], [320, 128], [360, 108], [400, 116], [440, 96],
  [480, 150], [520, 178], [560, 168], [600, 172], [640, 150], [680, 156],
  [720, 132], [760, 138], [800, 112], [840, 118], [880, 92], [920, 98],
  [960, 74],
];

const PATH = POINTS.reduce(
  (d, [x, y], i) => (i === 0 ? `M ${x} ${y}` : `${d} L ${x} ${y}`),
  "",
);

const SHOCK_X = 480;

export function MarketSequence() {
  const root = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState(0);
  const [reduced, setReduced] = useState(false);

  useGSAP(
    () => {
      const line = root.current?.querySelector<SVGPathElement>("[data-line]");
      const shock = root.current?.querySelector<SVGGElement>("[data-shock]");
      const sweep = root.current?.querySelector<SVGLineElement>("[data-sweep]");
      if (!line || !shock || !sweep) return;

      const length = line.getTotalLength();

      // Under reduced motion the figure is presented finished: the line fully
      // drawn, the shock marked, and every note expanded — no pin, no scrub.
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        gsap.set(line, { strokeDasharray: "none", strokeDashoffset: 0 });
        gsap.set(shock, { opacity: 1, scale: 1, transformOrigin: "center" });
        gsap.set(sweep, { opacity: 0 });
        setReduced(true);
        return;
      }

      gsap.set(line, { strokeDasharray: length, strokeDashoffset: length });
      gsap.set(shock, { opacity: 0, scale: 0.4, transformOrigin: "center" });

      const timeline = gsap.timeline({
        scrollTrigger: {
          trigger: root.current,
          start: "top top",
          end: "+=2600",
          pin: true,
          scrub: 0.6,
          anticipatePin: 1,
          onUpdate: (self) => {
            const index = Math.min(
              STEPS.length - 1,
              Math.floor(self.progress * STEPS.length),
            );
            setStep(index);
          },
        },
      });

      timeline
        .to(line, { strokeDashoffset: 0, ease: "none", duration: 1 }, 0)
        .to(sweep, { attr: { x1: 960, x2: 960 }, ease: "none", duration: 1 }, 0)
        .to(shock, { opacity: 1, scale: 1, duration: 0.06, ease: "back.out(2)" }, 0.47);
    },
    { scope: root },
  );

  return (
    <div
      ref={root}
      className="relative flex min-h-screen items-center border-y border-line bg-ink-900"
    >
      <div className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-16 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:gap-14">
        {/* Narration */}
        <div className="flex flex-col justify-center">
          <p className="eyebrow mb-5">The mechanism</p>

          <ol className="space-y-4">
            {STEPS.map((s, i) => {
              const active = reduced || i === step;
              return (
                <li
                  key={s.label}
                  className={`border-l-2 pl-4 transition-colors duration-300 ${
                    active ? "border-brass" : "border-line"
                  }`}
                >
                  <div className="flex items-baseline gap-3">
                    <span
                      className={`tabular text-[11px] tracking-widest transition-colors duration-300 ${
                        active ? "text-brass" : "text-faint"
                      }`}
                    >
                      {s.label}
                    </span>
                    <h3
                      className={`font-display text-lg transition-colors duration-300 ${
                        active ? "text-text" : "text-faint"
                      }`}
                    >
                      {s.title}
                    </h3>
                  </div>

                  <div
                    className="grid transition-all duration-500"
                    style={{
                      gridTemplateRows: active ? "1fr" : "0fr",
                      opacity: active ? 1 : 0,
                    }}
                  >
                    <p className="overflow-hidden text-[15px] leading-relaxed text-muted">
                      <span className="block pt-2">{s.body}</span>
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>

        {/* Instrument */}
        <div className="flex items-center">
          <figure className="w-full border border-line bg-ink-800">
            <figcaption className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
              <span className="eyebrow">FRGE · Forgeworks</span>
              <span className="tabular text-xs text-faint">
                30-day simulated close
              </span>
            </figcaption>

            <div className="engraved p-4">
              <svg
                viewBox="0 0 960 200"
                className="h-56 w-full sm:h-72"
                role="img"
                aria-label="Simulated 30-day price line for Forgeworks, showing a sharp fall at a market shock on day fourteen followed by recovery and a rising trend."
              >
                {/* Baseline rules */}
                {[40, 100, 160].map((y) => (
                  <line
                    key={y}
                    x1="0"
                    y1={y}
                    x2="960"
                    y2={y}
                    stroke="var(--line)"
                    strokeWidth="1"
                  />
                ))}

                <path
                  data-line
                  d={PATH}
                  fill="none"
                  stroke="var(--brass)"
                  strokeWidth="2.5"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />

                {/* Scrubbing playhead */}
                <line
                  data-sweep
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="200"
                  stroke="var(--line-strong)"
                  strokeWidth="1"
                  strokeDasharray="3 4"
                />

                {/* Shock marker */}
                <g data-shock>
                  <line
                    x1={SHOCK_X}
                    y1="8"
                    x2={SHOCK_X}
                    y2="192"
                    stroke="var(--loss)"
                    strokeWidth="1"
                    strokeDasharray="2 4"
                  />
                  <rect
                    x={SHOCK_X - 1}
                    y="140"
                    width="2"
                    height="2"
                    fill="var(--loss)"
                  />
                  <circle
                    cx={SHOCK_X}
                    cy="150"
                    r="5"
                    fill="var(--ink-800)"
                    stroke="var(--loss)"
                    strokeWidth="2"
                  />
                  <text
                    x={SHOCK_X + 12}
                    y="30"
                    fill="var(--loss)"
                    fontSize="11"
                    fontFamily="var(--font-mono)"
                    letterSpacing="0.08em"
                  >
                    LABOR STRIKE · IRONPEAK
                  </text>
                </g>
              </svg>
            </div>

            <div className="grid grid-cols-3 border-t border-line">
              {[
                ["Severity", "0.62"],
                ["Duration", "9 days"],
                ["Sector", "machinery"],
              ].map(([k, v]) => (
                <div key={k} className="border-r border-line px-4 py-3 last:border-r-0">
                  <div className="eyebrow mb-1">{k}</div>
                  <div className="tabular text-sm text-text">{v}</div>
                </div>
              ))}
            </div>
          </figure>
        </div>
      </div>
    </div>
  );
}

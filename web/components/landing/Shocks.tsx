"use client";

import ScrollFloat from "../reactbits/ScrollFloat";
import AnimatedContent from "../reactbits/AnimatedContent";

/** The seven event classes the engine can draw, with who they hurt and help. */
const SHOCKS = [
  {
    name: "Weather shock",
    resources: "food, timber",
    hurt: "farming, shipping",
    helped: "insurance",
  },
  {
    name: "Cyberattack",
    resources: "credit",
    hurt: "finance, transport",
    helped: "security",
  },
  {
    name: "Credit crunch",
    resources: "credit",
    hurt: "construction, finance",
    helped: "insurance",
  },
  {
    name: "Labor strike",
    resources: "food",
    hurt: "mining, machinery",
    helped: "finance",
  },
  {
    name: "Technology breakthrough",
    resources: "energy",
    hurt: "machinery",
    helped: "transport",
  },
  {
    name: "Regulatory reform",
    resources: "credit",
    hurt: "finance",
    helped: "insurance",
  },
  {
    name: "Corporate scandal",
    resources: "credit",
    hurt: "finance",
    helped: "security",
  },
];

export function Shocks() {
  return (
    <section className="border-b border-line bg-ink-800 py-24">
      <div className="mx-auto max-w-6xl px-5">
        <div className="mb-3 flex items-center gap-3">
          <span className="h-px w-10 bg-brass-dim" aria-hidden />
          <p className="eyebrow">The wire</p>
        </div>

        <ScrollFloat
          containerClassName="!my-0 mb-4"
          textClassName="!font-[family-name:var(--font-display)] !text-[clamp(1.75rem,4vw,2.5rem)] !font-normal leading-tight text-text"
          animationDuration={1}
          ease="back.inOut(1.6)"
          scrollStart="center bottom+=42%"
          scrollEnd="bottom bottom-=32%"
          stagger={0.024}
        >
          Every shock has a winner.
        </ScrollFloat>

        <p className="mb-10 max-w-2xl text-[15px] leading-relaxed text-muted">
          Events are drawn per day with a severity between 0.25 and 0.85 and a
          duration of three to twelve days. Read the sector table and a
          catastrophe for one house becomes a position in another.
        </p>

        <div className="grid gap-px border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {SHOCKS.map((s, i) => (
            <AnimatedContent
              key={s.name}
              distance={22}
              duration={0.5}
              ease="power2.out"
              initialOpacity={0}
              threshold={0.08}
              delay={(i % 3) * 0.06}
            >
              <article className="h-full bg-ink-800 p-5 transition-colors duration-200 hover:bg-ink-700">
                <h3 className="mb-4 font-display text-lg text-text">{s.name}</h3>
                <dl className="space-y-2 text-[13px]">
                  <div className="flex gap-2">
                    <dt className="w-20 shrink-0 text-faint">Resources</dt>
                    <dd className="tabular text-muted">{s.resources}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="w-20 shrink-0 text-faint">Hurt</dt>
                    <dd className="tabular text-loss">{s.hurt}</dd>
                  </div>
                  <div className="flex gap-2">
                    <dt className="w-20 shrink-0 text-faint">Helped</dt>
                    <dd className="tabular text-gain">{s.helped}</dd>
                  </div>
                </dl>
              </article>
            </AnimatedContent>
          ))}

          {/* Fills the final cell of the 3-column grid at large sizes. */}
          <div className="hidden bg-ink-800 p-5 lg:flex lg:items-end">
            <p className="font-display text-[15px] italic leading-relaxed text-faint">
              &ldquo;A shock is only a loss if you were standing where it
              landed.&rdquo;
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

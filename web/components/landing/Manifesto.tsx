"use client";

import ScrollReveal from "../reactbits/ScrollReveal";

/**
 * A single editorial statement that resolves word by word as the reader
 * descends. The blur is disabled — words gain weight and settle upright,
 * which reads as type being set rather than as an effect.
 */
export function Manifesto() {
  return (
    <section
      id="mechanism"
      className="border-b border-line bg-ink-900 py-24 sm:py-32"
    >
      <div className="mx-auto max-w-4xl px-5">
        <div className="mb-10 flex items-center gap-3">
          <span className="h-px w-10 bg-brass-dim" aria-hidden />
          <p className="eyebrow">The premise</p>
        </div>

        <ScrollReveal
          enableBlur={false}
          baseOpacity={0.12}
          baseRotation={2}
          rotationEnd="bottom 62%"
          wordAnimationEnd="bottom 68%"
          containerClassName="!my-0"
          textClassName="!font-[family-name:var(--font-display)] !text-[clamp(1.6rem,3.6vw,2.9rem)] !leading-[1.3] !font-normal text-text"
        >
          Most trading games reward the fastest click. This one rewards the
          steadier hand: prices here answer to profit, inventory and interest,
          shocks arrive with a region and a severity, and every run is seeded so
          the market can be studied rather than merely survived.
        </ScrollReveal>
      </div>
    </section>
  );
}

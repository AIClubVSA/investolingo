"use client";

import Link from "next/link";
import SplitText from "../reactbits/SplitText";
import DecryptedText from "../reactbits/DecryptedText";

/**
 * The hero states the proposition plainly. Motion is limited to the headline
 * settling and the standfirst resolving — the backdrop is an engraved rule
 * grid rather than the usual luminous wash.
 */
export function Hero() {
  return (
    <section className="relative flex min-h-[92vh] items-center overflow-hidden border-b border-line">
      <div className="engraved absolute inset-0 opacity-40" aria-hidden />
      {/* Flat vignette: a solid plane at low alpha, not a colour ramp. */}
      <div
        className="absolute inset-0 bg-ink-900/55"
        aria-hidden
      />

      <div className="relative mx-auto w-full max-w-6xl px-5 pt-24 pb-16">
        <div className="max-w-3xl">
          <div className="mb-7 flex items-center gap-3">
            <span className="h-px w-10 bg-brass-dim" aria-hidden />
            <p className="eyebrow">Est. 2026 · The Aether Exchange</p>
          </div>

          <SplitText
            tag="h1"
            text="Trade the ledger, not the hype."
            textAlign="left"
            className="font-display text-5xl leading-[1.06] tracking-tight text-text sm:text-6xl md:text-7xl"
            splitType="words"
            delay={38}
            duration={0.9}
            ease="power3.out"
            from={{ opacity: 0, y: 28 }}
            to={{ opacity: 1, y: 0 }}
            threshold={0.05}
            rootMargin="0px"
          />

          <div className="mt-7 max-w-xl text-[17px] leading-relaxed text-muted">
            <DecryptedText
              text="A deterministic market simulation. Ten chartered houses, seven kinds of shock, and a thirty-day ledger that keeps an honest account of every decision you make."
              animateOn="view"
              sequential
              revealDirection="start"
              speed={12}
              maxIterations={8}
              useOriginalCharsOnly
              className="text-muted"
              encryptedClassName="text-faint"
              parentClassName="leading-relaxed"
            />
          </div>

          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link
              href="/terminal"
              className="cursor-pointer border border-brass bg-brass px-7 py-3 text-[13px] font-bold uppercase tracking-[0.14em] text-ink-900 transition-colors duration-200 hover:border-brass-bright hover:bg-brass-bright"
            >
              Enter the terminal
            </Link>
            <a
              href="#mechanism"
              className="cursor-pointer border border-line px-7 py-3 text-[13px] font-bold uppercase tracking-[0.14em] text-muted transition-colors duration-200 hover:border-line-strong hover:text-text"
            >
              Read the prospectus
            </a>
          </div>

          <dl className="mt-14 grid max-w-2xl grid-cols-2 gap-x-8 gap-y-6 border-t border-line pt-8 sm:grid-cols-4">
            {[
              ["100,000", "Opening capital"],
              ["10", "Listed houses"],
              ["7", "Shock classes"],
              ["0.10%", "Commission"],
            ].map(([value, label]) => (
              <div key={label}>
                <dt className="tabular text-2xl text-text">{value}</dt>
                <dd className="eyebrow mt-1.5">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}

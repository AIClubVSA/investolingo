import Link from "next/link";
import { Nav } from "@/components/Nav";
import { TickerTape } from "@/components/TickerTape";
import { MarketSequence } from "@/components/MarketSequence";
import { Hero } from "@/components/landing/Hero";
import { Manifesto } from "@/components/landing/Manifesto";
import { Progression } from "@/components/landing/Progression";
import { Shocks } from "@/components/landing/Shocks";
import { Houses } from "@/components/landing/Houses";

export default function Home() {
  return (
    <>
      <Nav />
      <main className="flex-1">
        <Hero />
        <TickerTape />
        <Manifesto />
        <MarketSequence />
        <Houses />
        <Shocks />
        <Progression />

        {/* Closing */}
        <section className="border-t border-line bg-ink-800">
          <div className="mx-auto max-w-3xl px-5 py-24 text-center">
            <p className="eyebrow mb-6">Open an account</p>
            <h2 className="font-display text-4xl leading-tight text-text sm:text-5xl">
              One hundred thousand in cleared funds.
              <br />
              <span className="italic text-brass">Thirty days to prove it.</span>
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-[15px] leading-relaxed text-muted">
              The exchange opens on 7 September 2026. Every run is seeded, so the
              same decisions produce the same market — and the difference in
              outcome is only ever you.
            </p>
            <Link
              href="/terminal"
              className="mt-9 inline-block cursor-pointer border border-brass bg-brass px-8 py-3 text-[13px] font-bold uppercase tracking-[0.14em] text-ink-900 transition-colors duration-200 hover:border-brass-bright hover:bg-brass-bright"
            >
              Enter the terminal
            </Link>
          </div>
        </section>

        <footer className="border-t border-line bg-ink-900">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-xs text-faint sm:flex-row sm:items-center sm:justify-between">
            <p>
              <span className="font-display text-sm text-muted">TradeQuest</span>
              {" — a fictional market simulation. Not investment advice."}
            </p>
            <p className="tabular">Aether Exchange · engine v4 · seed 20260907</p>
          </div>
        </footer>
      </main>
    </>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const LINKS = [
  { href: "/", label: "Prospectus" },
  { href: "/terminal", label: "Terminal" },
];

export function Nav() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 border-b transition-colors duration-200 ${
        scrolled
          ? "border-line bg-ink-900/95 backdrop-blur-sm"
          : "border-transparent bg-transparent"
      }`}
    >
      <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5">
        <Link
          href="/"
          className="group flex items-baseline gap-2 cursor-pointer"
          aria-label="TradeQuest home"
        >
          <span className="font-display text-lg font-semibold tracking-tight text-text">
            TradeQuest
          </span>
          <span className="hidden text-[10px] uppercase tracking-[0.2em] text-faint transition-colors duration-200 group-hover:text-brass sm:inline">
            Aether Exchange
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`cursor-pointer px-3 py-1.5 text-[13px] transition-colors duration-200 ${
                  active
                    ? "text-brass"
                    : "text-muted hover:text-text"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <Link
            href="/terminal"
            className="ml-2 cursor-pointer border border-brass-dim px-3.5 py-1.5 text-[13px] font-bold uppercase tracking-[0.08em] text-brass transition-colors duration-200 hover:bg-brass hover:text-ink-900"
          >
            Open Account
          </Link>
        </div>
      </nav>
    </header>
  );
}

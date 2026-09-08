import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Terminal } from "@/components/terminal/Terminal";

export const metadata: Metadata = {
  title: "Terminal — TradeQuest",
  description:
    "Trade ten chartered houses on the Aether Exchange, advance the simulation day by day, and earn your standing.",
};

export default function TerminalPage() {
  return (
    <>
      <Nav />
      <main className="flex-1">
        <Terminal />
      </main>
    </>
  );
}

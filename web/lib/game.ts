/**
 * Client-side bindings for the Aether Exchange v4 simulation.
 *
 * Mirrors the shapes emitted by backend/aether_backend_v4.py. Progression
 * (level, XP, tier) is derived here rather than stored: the backend owns the
 * economy, the front end owns how that economy is narrated to the player.
 */

export const TICKERS = [
  { symbol: "IRON", house: "Ironpeak Extraction", sector: "mining", output: "metal" },
  { symbol: "EMBR", house: "Ember Power", sector: "energy", output: "energy" },
  { symbol: "FRGE", house: "Forgeworks", sector: "machinery", output: "metal" },
  { symbol: "VRDT", house: "Verdant Fields", sector: "farming", output: "food" },
  { symbol: "LEAF", house: "Leafline Botanicals", sector: "herbal", output: "food" },
  { symbol: "SAIL", house: "Sailfast Freight", sector: "shipping", output: "service" },
  { symbol: "BANK", house: "Crown Bank", sector: "finance", output: "credit" },
  { symbol: "AEGS", house: "Aegis Assurance", sector: "insurance", output: "service" },
  { symbol: "GATE", house: "Gatewell Transit", sector: "transport", output: "service" },
  { symbol: "WYRM", house: "Wyrmguard Security", sector: "security", output: "service" },
] as const;

export type Symbol = (typeof TICKERS)[number]["symbol"];

export const TICKER_INDEX = Object.fromEntries(
  TICKERS.map((t) => [t.symbol, t]),
) as Record<string, (typeof TICKERS)[number]>;

export const STARTING_CASH = 100_000;

export interface Position {
  ticker: string;
  quantity: number;
  price: number;
  value: number;
}

export interface Trade {
  day: number;
  side: "buy" | "sell";
  ticker: string;
  quantity: number;
  price: number;
  fee: number;
}

export interface Portfolio {
  cash: number;
  positions: Position[];
  value: number;
  profit: number;
  trades: Trade[];
  orders: unknown[];
}

export interface MarketEvent {
  id: string;
  type: string;
  name: string;
  region: string;
  severity: number;
  duration: number;
  day: number;
  resources: string[];
  sectors_hurt: string[];
  sectors_helped: string[];
}

export interface Company {
  cash: number;
  debt: number;
  inventory: number;
  profit: number;
  equity: number;
  bankrupt: boolean;
  strategy: "expand" | "defend" | "innovate";
  output: string;
  sector: string;
}

export interface Mission {
  id: string;
  name: string;
  goal: string;
  reward: number;
}

export interface MissionsResponse {
  missions: Mission[];
  completed: string[];
  rewards: number;
}

export interface GameState {
  version: number;
  seed: number;
  start_date: string;
  sim_day: number;
  prices: Record<string, number>;
  previous_prices: Record<string, number>;
  resources: Record<string, number>;
  inflation: number;
  interest_rate: number;
  currency: number;
  events: MarketEvent[];
  active_events: MarketEvent[];
  companies: Record<string, Company>;
  portfolio: {
    cash: number;
    holdings: Record<string, number>;
    trades: Trade[];
    orders: unknown[];
  };
  achievements: string[];
  mission_rewards: number;
  history: { day: number; prices: Record<string, number>; event: MarketEvent | null }[];
  updates: string[];
}

/* ------------------------------------------------------------------ */
/* Transport                                                           */
/* ------------------------------------------------------------------ */

export class BackendOffline extends Error {}

async function call<T>(endpoint: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/game/${endpoint}`, {
    ...init,
    cache: "no-store",
  });
  const body = await response.json().catch(() => ({}));

  if (response.status === 503) {
    throw new BackendOffline(body.error ?? "Simulation backend unreachable");
  }
  if (!response.ok) {
    throw new Error(body.error ?? `Request to ${endpoint} failed`);
  }
  return body as T;
}

export const api = {
  state: () => call<GameState>("state"),
  portfolio: () => call<Portfolio>("portfolio"),
  missions: () => call<MissionsResponse>("missions"),

  advance: (days = 1) =>
    call<{ day: number; event: MarketEvent | null; portfolio: Portfolio }>(
      "advance",
      { method: "POST", body: JSON.stringify({ days }) },
    ),

  trade: (side: "buy" | "sell", ticker: string, qty: number) =>
    call<Trade>("trade", {
      method: "POST",
      body: JSON.stringify({ side, ticker, qty }),
    }),

  reset: (seed = 20260907) =>
    call<{ ok: boolean }>("reset", {
      method: "POST",
      body: JSON.stringify({ seed }),
    }),
};

/* ------------------------------------------------------------------ */
/* Progression — derived, front-end owned                              */
/* ------------------------------------------------------------------ */

export const RANKS = [
  "Apprentice",
  "Clerk",
  "Broker",
  "Factor",
  "Merchant",
  "Magnate",
  "Governor",
] as const;

/**
 * XP is earned for participating, not merely for winning: days survived and
 * trades placed both count, so a cautious player still progresses. Realised
 * gains are weighted on top so skill still separates the field.
 */
export function experience(state: GameState | null, portfolio: Portfolio | null) {
  if (!state || !portfolio) return 0;
  const days = state.sim_day * 12;
  const trades = state.portfolio.trades.length * 25;
  const missions = state.achievements.length * 200;
  const gains = Math.max(0, portfolio.profit) * 0.05;
  return Math.floor(days + trades + missions + gains);
}

/** Levels widen as they climb, so early progress is quick and later ranks earn. */
export function levelFor(xp: number) {
  const level = Math.max(1, Math.floor(Math.sqrt(xp / 120)) + 1);
  const floor = (level - 1) ** 2 * 120;
  const ceiling = level ** 2 * 120;
  const progress = ceiling === floor ? 0 : (xp - floor) / (ceiling - floor);
  return {
    level,
    floor,
    ceiling,
    progress: Math.min(1, Math.max(0, progress)),
    rank: RANKS[Math.min(RANKS.length - 1, Math.floor((level - 1) / 2))],
  };
}

/* ------------------------------------------------------------------ */
/* Formatting                                                          */
/* ------------------------------------------------------------------ */

export const money = (n: number, decimals = 2) =>
  n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

export const signed = (n: number, decimals = 2) =>
  `${n >= 0 ? "+" : "−"}${money(Math.abs(n), decimals)}`;

export const percent = (n: number, decimals = 2) =>
  `${n >= 0 ? "+" : "−"}${Math.abs(n * 100).toFixed(decimals)}%`;

/** The simulation counts days from a fixed start date; render the real date. */
export function simDate(startDate: string, day: number) {
  const base = new Date(`${startDate}T00:00:00Z`);
  base.setUTCDate(base.getUTCDate() + day);
  return base.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}

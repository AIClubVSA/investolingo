"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import CountUp from "../reactbits/CountUp";
import ClickSpark from "../reactbits/ClickSpark";
import { PriceBoard } from "./PriceBoard";
import { TradeTicket } from "./TradeTicket";
import { Standing } from "./Standing";
import { EventWire } from "./EventWire";
import { AwardToast, type Award } from "./AwardToast";
import {
  BackendOffline,
  STARTING_CASH,
  api,
  experience,
  money,
  percent,
  signed,
  simDate,
  type GameState,
  type MissionsResponse,
  type Portfolio,
} from "@/lib/game";

const ADVANCE_STEPS = [1, 5, 30] as const;

export function Terminal() {
  const [state, setState] = useState<GameState | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [missions, setMissions] = useState<MissionsResponse | null>(null);

  const [selected, setSelected] = useState("IRON");
  const [busy, setBusy] = useState(false);
  const [tradeError, setTradeError] = useState<string | null>(null);
  const [offline, setOffline] = useState<string | null>(null);
  const [awards, setAwards] = useState<Award[]>([]);

  // Tracks which commissions had already been awarded, so a refresh does not
  // re-announce every seal the player earned in an earlier session.
  const seen = useRef<Set<string> | null>(null);
  const awardKey = useRef(0);

  const refresh = useCallback(async (announce: boolean) => {
    try {
      const [nextState, nextPortfolio, nextMissions] = await Promise.all([
        api.state(),
        api.portfolio(),
        api.missions(),
      ]);

      setOffline(null);
      setState(nextState);
      setPortfolio(nextPortfolio);
      setMissions(nextMissions);

      const completed = new Set(nextMissions.completed);
      if (seen.current === null) {
        seen.current = completed;
      } else if (announce) {
        const fresh = nextMissions.completed.filter(
          (id) => !seen.current!.has(id),
        );
        if (fresh.length) {
          setAwards((current) => [
            ...current,
            ...fresh.map((id) => {
              const mission = nextMissions.missions.find((m) => m.id === id);
              return {
                key: ++awardKey.current,
                id,
                name: mission?.name ?? id,
                reward: mission?.reward ?? 0,
              };
            }),
          ]);
        }
        seen.current = completed;
      } else {
        seen.current = completed;
      }
    } catch (error) {
      if (error instanceof BackendOffline) setOffline(error.message);
      else setOffline((error as Error).message);
    }
  }, []);

  useEffect(() => {
    // Initial load. Every setState in `refresh` runs after an await, so this
    // does not synchronously cascade — the lint rule cannot see through the
    // async boundary.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh(false);
  }, [refresh]);

  const advance = async (days: number) => {
    setBusy(true);
    setTradeError(null);
    try {
      await api.advance(days);
      await refresh(true);
    } catch (error) {
      setOffline(
        error instanceof BackendOffline ? error.message : (error as Error).message,
      );
    } finally {
      setBusy(false);
    }
  };

  const trade = async (side: "buy" | "sell", qty: number) => {
    setBusy(true);
    setTradeError(null);
    try {
      await api.trade(side, selected, qty);
      await refresh(true);
    } catch (error) {
      if (error instanceof BackendOffline) setOffline(error.message);
      else setTradeError((error as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    setBusy(true);
    try {
      await api.reset();
      seen.current = null;
      setAwards([]);
      await refresh(false);
    } catch (error) {
      setOffline(
        error instanceof BackendOffline ? error.message : (error as Error).message,
      );
    } finally {
      setBusy(false);
    }
  };

  const dismiss = useCallback((key: number) => {
    setAwards((current) => current.filter((a) => a.key !== key));
  }, []);

  if (offline && !state) {
    return <Offline message={offline} onRetry={() => refresh(false)} />;
  }

  if (!state || !portfolio || !missions) {
    return <Loading />;
  }

  const xp = experience(state, portfolio);
  const returnPct = portfolio.profit / STARTING_CASH;
  const invested = portfolio.value - portfolio.cash;

  return (
    <ClickSpark
      sparkColor="#b8933a"
      sparkSize={7}
      sparkRadius={16}
      sparkCount={6}
      duration={380}
    >
      <div className="min-h-screen pt-14">
        {offline ? (
          <p
            role="alert"
            className="border-b border-loss/40 bg-loss/10 px-5 py-2 text-center text-[13px] text-loss"
          >
            {offline}
          </p>
        ) : null}

        {/* Status strip */}
        <div className="border-b border-line bg-ink-800">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-3">
            <div className="flex flex-wrap items-baseline gap-x-7 gap-y-2">
              <Stat label="Session" value={`Day ${state.sim_day}`} accent />
              <Stat
                label="Date"
                value={simDate(state.start_date, state.sim_day)}
              />
              <Stat
                label="Inflation"
                value={`${(state.inflation * 100).toFixed(2)}%`}
              />
              <Stat
                label="Base rate"
                value={`${(state.interest_rate * 100).toFixed(2)}%`}
              />
              <Stat label="Currency" value={state.currency.toFixed(4)} />
            </div>

            <div className="flex items-center gap-2">
              {ADVANCE_STEPS.map((days) => (
                <button
                  key={days}
                  type="button"
                  disabled={busy}
                  onClick={() => advance(days)}
                  className="cursor-pointer border border-line px-3.5 py-1.5 text-[12px] font-bold uppercase tracking-[0.1em] text-muted transition-colors duration-200 hover:border-brass-dim hover:text-brass disabled:cursor-not-allowed disabled:text-faint"
                >
                  +{days}d
                </button>
              ))}
              <button
                type="button"
                disabled={busy}
                onClick={reset}
                className="ml-1 cursor-pointer px-2 py-1.5 text-[12px] text-faint transition-colors duration-200 hover:text-loss disabled:cursor-not-allowed"
              >
                Reset
              </button>
            </div>
          </div>
        </div>

        {/* Valuation */}
        <div className="border-b border-line bg-ink-900">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-px bg-line sm:grid-cols-4">
            {[
              {
                label: "Account value",
                node: (
                  <CountUp
                    to={portfolio.value}
                    duration={0.8}
                    separator=","
                    className="tabular"
                  />
                ),
                tone: "text-text",
              },
              {
                label: "Cash",
                node: money(portfolio.cash),
                tone: "text-text",
              },
              {
                label: "Invested",
                node: money(invested),
                tone: "text-text",
              },
              {
                label: "Profit and loss",
                node: `${signed(portfolio.profit)} · ${percent(returnPct)}`,
                tone:
                  portfolio.profit > 0
                    ? "text-gain"
                    : portfolio.profit < 0
                      ? "text-loss"
                      : "text-muted",
              },
            ].map((cell) => (
              <div key={cell.label} className="bg-ink-900 px-5 py-4">
                <div className="eyebrow mb-1.5">{cell.label}</div>
                <div className={`tabular text-xl ${cell.tone}`}>{cell.node}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Working area */}
        <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 lg:grid-cols-[minmax(0,1fr)_21rem]">
          <div className="flex flex-col gap-5">
            <PriceBoard
              prices={state.prices}
              previous={state.previous_prices}
              companies={state.companies}
              holdings={state.portfolio.holdings}
              selected={selected}
              onSelect={setSelected}
            />

            <Positions portfolio={portfolio} />

            <EventWire
              events={state.events}
              active={state.active_events}
              day={state.sim_day}
            />
          </div>

          <aside className="flex flex-col gap-5">
            <TradeTicket
              ticker={selected}
              price={state.prices[selected] ?? 0}
              cash={portfolio.cash}
              held={state.portfolio.holdings[selected] ?? 0}
              busy={busy}
              error={tradeError}
              onSubmit={trade}
            />

            <Standing
              xp={xp}
              missions={missions.missions}
              completed={missions.completed}
              rewards={missions.rewards}
            />
          </aside>
        </div>

        <AwardToast awards={awards} onDismiss={dismiss} />
      </div>
    </ClickSpark>
  );
}

function Stat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div>
      <div className="eyebrow mb-0.5">{label}</div>
      <div className={`tabular text-sm ${accent ? "text-brass" : "text-text"}`}>
        {value}
      </div>
    </div>
  );
}

function Positions({ portfolio }: { portfolio: Portfolio }) {
  const open = portfolio.positions.filter((p) => p.quantity > 0);

  return (
    <div className="border border-line bg-ink-800">
      <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
        <h2 className="eyebrow">Positions</h2>
        <span className="tabular text-xs text-faint">
          {portfolio.trades.length} fills
        </span>
      </div>

      {open.length === 0 ? (
        <p className="px-4 py-6 text-[13px] text-faint">
          No open positions. Select a house on the board and place an order.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-[4.5rem_minmax(0,1fr)_6rem_7rem] gap-x-2 border-b border-line px-4 py-2">
            {["Symbol", "", "Qty", "Value"].map((h, i) => (
              <div
                key={i}
                className={`eyebrow ${i >= 2 ? "text-right" : ""}`}
              >
                {h}
              </div>
            ))}
          </div>
          {open.map((p) => (
            <div
              key={p.ticker}
              className="grid grid-cols-[4.5rem_minmax(0,1fr)_6rem_7rem] gap-x-2 border-b border-line px-4 py-2.5 last:border-b-0"
            >
              <span className="font-mono text-sm font-semibold tracking-wider text-brass">
                {p.ticker}
              </span>
              <span className="tabular text-[13px] text-faint">
                @ {money(p.price)}
              </span>
              <span className="tabular text-right text-sm text-text">
                {p.quantity}
              </span>
              <span className="tabular text-right text-sm text-text">
                {money(p.value)}
              </span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center pt-14">
      <div className="w-full max-w-sm px-5">
        <p className="eyebrow mb-4">Connecting to the exchange</p>
        <div className="flex gap-[3px]">
          {Array.from({ length: 24 }).map((_, i) => (
            <span
              key={i}
              className="tick h-6 flex-1 bg-ink-600"
              style={{ animationDelay: `${i * 60}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function Offline({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center px-5 pt-14">
      <div className="w-full max-w-lg border border-line bg-ink-800 p-6">
        <p className="eyebrow mb-3 text-loss">Exchange closed</p>
        <h1 className="mb-3 font-display text-2xl text-text">
          The simulation engine is not answering.
        </h1>
        <p className="mb-5 text-[14px] leading-relaxed text-muted">{message}</p>
        <pre className="tabular mb-5 overflow-x-auto border border-line bg-ink-900 p-3 text-[12px] text-brass">
          python3 backend/aether_backend_v4.py --server --port 8000
        </pre>
        <button
          type="button"
          onClick={onRetry}
          className="cursor-pointer border border-brass bg-brass px-6 py-2.5 text-[12px] font-bold uppercase tracking-[0.14em] text-ink-900 transition-colors duration-200 hover:bg-brass-bright"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

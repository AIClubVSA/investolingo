# TradeQuest

A deterministic market simulation game built on the Aether Exchange engine.
Ten fictional chartered houses, seven classes of shock, and a thirty-day ledger
that keeps an honest account of every decision the player makes.

Formerly `investolingo`. The product name throughout the interface is
**TradeQuest**; the GitHub repository still carries the old name (see
[Renaming the repository](#renaming-the-repository)).

## Layout

```
backend/    Aether Exchange v4 simulation — economy, events, missions, HTTP API
web/        Next.js 16 front end — prospectus site and trading terminal
```

The two files at the repository root (`aether_backend.py`,
`aether_feedwatch.py`) are the earlier v3 news-driven simulation. They are kept
for reference; **v4 in `backend/` is what the site runs against.**

## Running it

The site needs both processes. Start the engine first:

```bash
python3 backend/aether_backend_v4.py --server --port 8000
```

Then the front end:

```bash
npm --prefix web install
npm --prefix web run dev
```

Open http://localhost:3000. If the engine is not running, the terminal shows an
"Exchange closed" panel with the command to start it rather than failing
silently.

Point the front end at a different engine with `AETHER_BACKEND_URL`
(default `http://127.0.0.1:8000`).

## Tests

The suite imports the engine as a top-level module, so run it from inside
`backend/`:

```bash
cd backend && python3 -m unittest -v test_aether_backend_v4
```

Covers deterministic advancement, buy/sell with commission, mission unlocks,
state persistence, and the short-selling rejection.

## Engine API

The front end talks to the engine through a same-origin proxy at
`/api/game/*`, so the browser never needs the engine's address.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/state` | Full simulation state |
| GET | `/portfolio` | Cash, positions, valuation, fills |
| GET | `/prices` | Current marks |
| GET | `/companies` | Balance sheets and strategies |
| GET | `/events` | Every shock drawn so far |
| GET | `/missions` | Missions, completions, grants paid |
| POST | `/advance` | `{ "days": 1 }` — step the simulation |
| POST | `/trade` | `{ "side", "ticker", "qty" }` |
| POST | `/reset` | `{ "seed": 20260907 }` |

Note that the engine awards missions inside `advance()`, not `execute()` — a
commission is recognised on the next day tick after its condition is met.

## Design

The interface is deliberately formal: a flat institutional palette, hairline
rules instead of shadows, and **no gradients anywhere**. Surfaces are separated
by borders alone.

- **Type** — EB Garamond (display), Lato (interface), IBM Plex Mono (all
  figures, with tabular numerals so price columns align).
- **Colour** — a cool ink scale, one brass accent used sparingly, and
  desaturated green/red reserved for market semantics.
- **Tokens** — defined once in `web/app/globals.css` and exposed to Tailwind v4
  through `@theme inline`.

### Motion

Gamified and scroll-driven animation is built on
[React Bits](https://reactbits.dev) components, vendored into
`web/components/reactbits/` from the registry
(`https://reactbits.dev/r/{name}.json`) and left otherwise unmodified so they
can be re-pulled.

| Where | Effect |
| --- | --- |
| Hero | `SplitText` headline, `DecryptedText` standfirst |
| Ticker tape | `ScrollVelocity` — drifts, and accelerates with scroll |
| Premise | `ScrollReveal` — words gain weight as they are read |
| Mechanism | GSAP `ScrollTrigger` pin: scroll draws a 30-day price line, lands a shock marker, and advances the narration |
| Listings / wire | `AnimatedContent` — rows post in sequence |
| Terminal | `CountUp` valuations, ledger flash on every price tick, `ClickSpark` on interaction |
| Commissions | Engraved seal struck in on award, with a posted notice |

Under `prefers-reduced-motion`, CSS transitions and keyframes (the ledger
flash, the seal strike, the toast slide) are reduced to nothing, the pinned
scroll sequence is skipped entirely — the figure renders finished, with every
note expanded — and the commission demonstration on the prospectus awards all
three seals at once instead of in sequence. The vendored React Bits components
remain scroll-linked rather than autonomous, so they advance only as the reader
scrolls.

### Progression

The engine owns the economy; the front end owns how it is narrated. Experience
is derived in `web/lib/game.ts` from days survived, trades placed, commissions
earned and realised gains, then mapped onto seven ranks from Apprentice to
Governor. Nothing about progression is written back to the engine.

## Renaming the repository

The remote is still `AIClubVSA/investolingo`. Renaming a public repository is
outward-facing and affects anyone with a clone, so it has been left alone —
rename it in the GitHub settings when you are ready, then:

```bash
git remote set-url origin https://github.com/AIClubVSA/tradequest.git
```

## Disclaimer

TradeQuest is a fictional simulation for education and entertainment. It is not
investment advice, and the houses, prices and events in it do not correspond to
any real security or market.

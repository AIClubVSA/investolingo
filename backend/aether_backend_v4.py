#!/usr/bin/env python3
"""Backend-only Aether Exchange v4 simulation.

Run: python aether_backend_v4.py --play
API: python aether_backend_v4.py --server --port 8000
"""
from __future__ import annotations
import argparse, json, random, threading
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TICKERS = {
    "IRON": (184.0, "mining", "metal"), "EMBR": (276.4, "energy", "energy"),
    "FRGE": (231.5, "machinery", "metal"), "VRDT": (77.2, "farming", "food"),
    "LEAF": (312.8, "herbal", "food"), "SAIL": (167.3, "shipping", "service"),
    "BANK": (204.0, "finance", "credit"), "AEGS": (158.9, "insurance", "service"),
    "GATE": (341.0, "transport", "service"), "WYRM": (125.3, "security", "service"),
}
EVENTS = [
    ("weather_shock", "Weather shock", ("food", "timber"), ("farming", "shipping"), ("insurance",)),
    ("cyberattack", "Cyberattack", ("credit",), ("finance", "transport"), ("security",)),
    ("credit_crunch", "Credit crunch", ("credit",), ("construction", "finance"), ("insurance",)),
    ("labor_strike", "Labor strike", ("food",), ("mining", "machinery"), ("finance",)),
    ("tech_breakthrough", "Technology breakthrough", ("energy",), ("machinery",), ("transport",)),
    ("regulation", "Regulatory reform", ("credit",), ("finance",), ("insurance",)),
    ("scandal", "Corporate scandal", ("credit",), ("finance",), ("security",)),
]
MISSIONS = [
    {"id": "first_trade", "name": "First Trade", "goal": "Execute one trade", "reward": 500},
    {"id": "diversified", "name": "Diversified", "goal": "Hold three companies", "reward": 1500},
    {"id": "survivor", "name": "Market Survivor", "goal": "Advance thirty days", "reward": 2500},
]

def rnd(seed, *parts):
    return random.Random(f"{seed}|{'|'.join(map(str, parts))}")

def new_state(seed=20260907, start_date="2026-09-07"):
    prices = {t: v[0] for t, v in TICKERS.items()}
    companies = {}
    for i, (t, (p, sector, output)) in enumerate(TICKERS.items()):
        companies[t] = {"cash": p * 100000, "debt": p * 60000, "inventory": 1000.,
                        "profit": 0., "equity": p * 40000, "bankrupt": False,
                        "strategy": ["expand", "defend", "innovate"][i % 3],
                        "output": output, "sector": sector}
    return {"version": 4, "seed": seed, "start_date": start_date, "sim_day": 0,
            "prices": prices, "previous_prices": dict(prices),
            "resources": {r: 100. for r in ("food", "metal", "timber", "energy", "credit")},
            "inflation": 0.02, "interest_rate": 0.04, "currency": 1.0,
            "events": [], "active_events": [], "companies": companies,
            "portfolio": {"cash": 100000., "holdings": {}, "trades": [], "orders": []},
            "achievements": [], "mission_rewards": 0, "history": [], "updates": []}

def portfolio_view(st):
    p = st["portfolio"]
    positions = []
    value = p["cash"]
    for t, qty in p["holdings"].items():
        price = st["prices"].get(t, 0.)
        positions.append({"ticker": t, "quantity": qty, "price": price, "value": round(qty * price, 2)})
        value += qty * price
    return {"cash": round(p["cash"], 2), "positions": positions,
            "value": round(value, 2), "profit": round(value - 100000, 2),
            "trades": p["trades"], "orders": p["orders"]}

def event_for(st, day):
    r = rnd(st["seed"], day, "event")
    if r.random() < .25: return None
    kind, name, resources, hurt, helped = r.choice(EVENTS)
    region = r.choice(("Ironpeak", "Verdant", "Azure", "Ember", "Crownlands"))
    severity = round(r.uniform(.25, .85), 2)
    return {"id": f"EV-{day:04d}-{kind}", "type": kind, "name": name, "region": region,
            "severity": severity, "duration": r.randint(3, 12), "day": day,
            "resources": resources, "sectors_hurt": hurt, "sectors_helped": helped}

def execute(st, side, ticker, qty, order_type="market", limit_price=None):
    ticker, qty = ticker.upper(), int(qty)
    if ticker not in TICKERS or qty <= 0 or side not in ("buy", "sell"):
        raise ValueError("Use buy/sell, a valid ticker, and positive quantity")
    price = st["prices"][ticker] if order_type == "market" else float(limit_price)
    if side == "buy" and order_type == "limit" and price < st["prices"][ticker]:
        raise ValueError("Limit buy is below the current simulated ask")
    if side == "sell" and st["portfolio"]["holdings"].get(ticker, 0) < qty:
        raise ValueError("Short selling is disabled; insufficient shares")
    fee = price * qty * .001
    total = price * qty + fee
    if side == "buy" and st["portfolio"]["cash"] < total:
        raise ValueError("Insufficient cash")
    st["portfolio"]["cash"] += -total if side == "buy" else price * qty - fee
    st["portfolio"]["holdings"][ticker] = st["portfolio"]["holdings"].get(ticker, 0) + (qty if side == "buy" else -qty)
    fill = {"day": st["sim_day"], "side": side, "ticker": ticker, "quantity": qty, "price": price, "fee": fee}
    st["portfolio"]["trades"].append(fill)
    return fill

def advance(st, days=1):
    for _ in range(days):
        day = st["sim_day"] + 1
        st["updates"] = []
        ev = event_for(st, day)
        if ev:
            st["events"].append(ev); st["active_events"].append(ev)
        r = rnd(st["seed"], day, "market")
        st["previous_prices"] = dict(st["prices"])
        for t, (base, sector, output) in TICKERS.items():
            c = st["companies"][t]
            shock = 0.
            if ev:
                if sector in ev["sectors_hurt"]: shock -= ev["severity"] * .08
                if sector in ev["sectors_helped"]: shock += ev["severity"] * .06
            strategy = c["strategy"]
            if strategy == "innovate": shock += .004
            if strategy == "expand": c["debt"] *= 1.001
            if strategy == "defend": c["cash"] *= 1.0005
            ret = shock + st["inflation"] * .02 + r.gauss(0, .012)
            st["prices"][t] = round(max(.01, st["prices"][t] * (1 + max(-.15, min(.15, ret)))), 2)
            c["profit"] = round(base * (.01 + ret), 2); c["equity"] += c["profit"]
            c["inventory"] = max(0., c["inventory"] + r.uniform(-30, 30) - shock * 100)
            if c["equity"] <= 0: c["bankrupt"] = True; st["prices"][t] = 0.
        st["inflation"] = max(0., min(.2, st["inflation"] + r.gauss(0, .001)))
        st["interest_rate"] = max(.005, min(.2, st["interest_rate"] + (st["inflation"] - .02) * .03))
        st["currency"] = round(st["currency"] * (1 - (st["inflation"] - .02) * .02), 6)
        for e in list(st["active_events"]):
            if day >= e["day"] + e["duration"]: st["active_events"].remove(e); st["updates"].append(f"{e['id']} resolved")
        ai_actions(st, day)
        st["sim_day"] = day
        st["history"].append({"day": day, "prices": dict(st["prices"]), "event": ev})
    update_progress(st)
    return {"day": st["sim_day"], "event": ev if days == 1 else None, "portfolio": portfolio_view(st)}

def ai_actions(st, day):
    r = rnd(st["seed"], day, "ai")
    for t, c in st["companies"].items():
        if c["bankrupt"]: continue
        if c["strategy"] == "innovate" and r.random() < .1: c["inventory"] += 100
        elif c["strategy"] == "expand" and r.random() < .08: c["debt"] *= 1.02
        elif c["strategy"] == "defend" and r.random() < .08: c["cash"] *= 1.01

def update_progress(st):
    p = st["portfolio"]
    checks = {"first_trade": bool(p["trades"]), "diversified": len([x for x in p["holdings"].values() if x > 0]) >= 3, "survivor": st["sim_day"] >= 30}
    for m in MISSIONS:
        if checks[m["id"]] and m["id"] not in st["achievements"]:
            st["achievements"].append(m["id"]); st["mission_rewards"] += m["reward"]; p["cash"] += m["reward"]

class Backend:
    def __init__(self, path=Path("aether_v4_state.json")):
        self.path, self.lock = path, threading.RLock()
        self.state = json.loads(path.read_text()) if path.exists() else new_state()
    def save(self): self.path.write_text(json.dumps(self.state, indent=2))

def make_handler(backend):
    class H(BaseHTTPRequestHandler):
        def send_json(self, code, data):
            raw = json.dumps(data).encode(); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers(); self.wfile.write(raw)
        def body(self):
            n = int(self.headers.get("Content-Length", 0)); return json.loads(self.rfile.read(n) or b"{}")
        def do_GET(self):
            with backend.lock:
                s = backend.state; path = self.path.split("?", 1)[0]
                data = {"/health": {"ok": True}, "/state": s, "/portfolio": portfolio_view(s), "/companies": s["companies"], "/prices": s["prices"], "/events": s["events"], "/missions": {"missions": MISSIONS, "completed": s["achievements"], "rewards": s["mission_rewards"]}}.get(path)
                self.send_json(200, data) if data is not None else self.send_json(404, {"error": "unknown endpoint"})
        def do_POST(self):
            try:
                with backend.lock:
                    s, path, b = backend.state, self.path.split("?", 1)[0], self.body()
                    if path == "/advance": out = advance(s, int(b.get("days", 1)))
                    elif path == "/trade": out = execute(s, b["side"], b["ticker"], b["qty"], b.get("order_type", "market"), b.get("limit_price"))
                    elif path == "/reset": backend.state = s = new_state(int(b.get("seed", 20260907))); out = {"ok": True}
                    else: self.send_json(404, {"error": "unknown endpoint"}); return
                    backend.save(); self.send_json(200, out)
            except (KeyError, ValueError) as e: self.send_json(400, {"error": str(e)})
    return H

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--server", action="store_true"); ap.add_argument("--port", type=int, default=8000); ap.add_argument("--days", type=int, default=0); ap.add_argument("--play", action="store_true"); args = ap.parse_args()
    b = Backend()
    if args.server:
        ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(b)).serve_forever()
    elif args.days: print(json.dumps(advance(b.state, args.days), indent=2)); b.save()
    else:
        print("Aether v4. Try: python aether_backend_v4.py --server"); print(json.dumps(portfolio_view(b.state), indent=2))
if __name__ == "__main__": main()

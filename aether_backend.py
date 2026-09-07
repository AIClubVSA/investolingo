#!/usr/bin/env python3
"""HTTP backend for the Aether Exchange simulation.

Run:
  python aether_backend.py --host 127.0.0.1 --port 8000

The backend intentionally depends only on Python's standard library and wraps
the simulation functions from aether_feedwatch.py.
"""

from __future__ import annotations

import argparse
import json
import threading
import traceback
from dataclasses import asdict, is_dataclass
from datetime import date, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import aether_feedwatch as sim


DEFAULT_STATE_PATH = Path("aether_backend_state.json")
DEFAULT_SEED = 20260907
DEFAULT_START_DATE = "2026-09-07"


class BackendState:
    def __init__(self, state_path: Path, seed: int, start_date: str):
        self.state_path = state_path
        self.seed = seed
        self.start_date = start_date
        self.lock = threading.RLock()
        self.state = sim.load_state(state_path, seed, start_date)

    def save(self) -> None:
        sim.save_state(self.state_path, self.state)

    def reset(self, seed: int | None = None, start_date: str | None = None) -> dict:
        if seed is not None:
            self.seed = seed
        if start_date is not None:
            date.fromisoformat(start_date)
            self.start_date = start_date
        self.state = sim.new_state(self.seed, self.start_date)
        self.save()
        return self.state


def json_default(value):
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def int_param(params: dict[str, list[str]], name: str, default: int, minimum: int | None = None) -> int:
    raw = params.get(name, [str(default)])[0]
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def portfolio_value(state: dict) -> float:
    portfolio = state["portfolio"]
    holdings_value = sum(qty * state["prices"].get(ticker, 0.0) for ticker, qty in portfolio["holdings"].items())
    return round(portfolio["cash"] + holdings_value, 2)


def state_summary(state: dict) -> dict:
    return {
        "version": state.get("version"),
        "seed": state["seed"],
        "start_date": state["start_date"],
        "sim_day": state["sim_day"],
        "sim_date": (date.fromisoformat(state["start_date"]) + timedelta(days=max(state["sim_day"] - 1, 0))).isoformat(),
        "events": len(state["events"]),
        "active_events": len(state["active"]),
        "prices": state["prices"],
        "last_return": state["last_return"],
        "resources": state["resources"],
        "portfolio_value": portfolio_value(state),
        "updates": state.get("updates", []),
    }


def companies_payload() -> list[dict]:
    companies = []
    for ticker, data in sim.COMPANIES.items():
        name, region, sectors, workforce, start_price, shares_out_millions = data
        companies.append({
            "ticker": ticker,
            "name": name,
            "region": region,
            "sectors": sectors,
            "workforce": workforce,
            "output": sim.OUTPUTS.get(ticker),
            "suppliers": sim.SUPPLIERS.get(ticker, []),
            "history": sim.HISTORIES.get(ticker, ""),
            "start_price": start_price,
            "shares_out_millions": shares_out_millions,
        })
    return companies


def build_handler(backend: BackendState):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AetherBackend/1.0"

        def log_message(self, fmt: str, *args) -> None:
            if not getattr(self.server, "quiet", False):
                super().log_message(fmt, *args)

        def _send_json(self, status: HTTPStatus, payload: dict | list) -> None:
            body = json.dumps(payload, ensure_ascii=False, default=json_default).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError("request body must be valid JSON") from exc
            if not isinstance(data, dict):
                raise ValueError("request body must be a JSON object")
            return data

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._send_json(status, {"error": message})

        def do_OPTIONS(self) -> None:
            self._send_json(HTTPStatus.NO_CONTENT, {})

        def do_GET(self) -> None:
            try:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                path = parsed.path.rstrip("/") or "/"

                with backend.lock:
                    state = backend.state
                    if path == "/health":
                        self._send_json(HTTPStatus.OK, {"ok": True})
                    elif path == "/state":
                        self._send_json(HTTPStatus.OK, state_summary(state))
                    elif path == "/companies":
                        self._send_json(HTTPStatus.OK, companies_payload())
                    elif path == "/prices":
                        self._send_json(HTTPStatus.OK, {"prices": state["prices"], "last_return": state["last_return"]})
                    elif path == "/resources":
                        self._send_json(HTTPStatus.OK, state["resources"])
                    elif path == "/events":
                        limit = int_param(params, "limit", 50, minimum=1)
                        self._send_json(HTTPStatus.OK, state["events"][-limit:])
                    elif path == "/portfolio":
                        self._send_json(HTTPStatus.OK, {**state["portfolio"], "value": portfolio_value(state)})
                    elif path == "/report":
                        self._send_json(HTTPStatus.OK, {
                            "summary": state_summary(state),
                            "active": state["active"],
                            "pending_effects": len(state["pending"]) + len(state["res_pending"]),
                            "economy": state["economy"],
                        })
                    else:
                        self._error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            except ValueError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
            except Exception:
                traceback.print_exc()
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

        def do_POST(self) -> None:
            try:
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"
                body = self._read_json()

                with backend.lock:
                    if path == "/advance":
                        days = int(body.get("days", 1))
                        if days < 1:
                            raise ValueError("days must be at least 1")
                        offline = bool(body.get("offline", True))
                        quiet = bool(body.get("quiet", True))
                        results = []
                        for _ in range(days):
                            events, notices = sim.run_day(backend.state, offline, quiet)
                            problems = sim.check_invariants(backend.state)
                            if problems:
                                raise RuntimeError("; ".join(problems))
                            results.append({"events": events, "notices": notices})
                        backend.save()
                        self._send_json(HTTPStatus.OK, {"summary": state_summary(backend.state), "days": results})
                    elif path == "/trade":
                        side = str(body.get("side", "")).lower()
                        ticker = str(body.get("ticker", "")).upper()
                        qty = int(body.get("qty", 0))
                        message = sim.trade(backend.state, side, ticker, qty)
                        problems = sim.check_invariants(backend.state)
                        if problems:
                            raise RuntimeError("; ".join(problems))
                        backend.save()
                        self._send_json(HTTPStatus.OK, {"message": message, "portfolio": {**backend.state["portfolio"], "value": portfolio_value(backend.state)}})
                    elif path == "/reset":
                        seed = body.get("seed")
                        start_date = body.get("start_date")
                        state = backend.reset(int(seed) if seed is not None else None, str(start_date) if start_date else None)
                        self._send_json(HTTPStatus.OK, state_summary(state))
                    else:
                        self._error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            except ValueError as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
            except RuntimeError as exc:
                self._error(HTTPStatus.CONFLICT, str(exc))
            except Exception:
                traceback.print_exc()
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal server error")

    return Handler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Aether Exchange HTTP backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    date.fromisoformat(args.start_date)
    backend = BackendState(args.state, args.seed, args.start_date)
    handler = build_handler(backend)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server.quiet = args.quiet
    print(f"Aether backend listening on http://{args.host}:{args.port}")
    print(f"State file: {args.state}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping backend.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

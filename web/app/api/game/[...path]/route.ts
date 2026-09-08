import { NextRequest, NextResponse } from "next/server";

/**
 * Thin proxy to the Aether Exchange v4 Python backend.
 *
 * Keeping the simulation behind a same-origin route means the browser never
 * needs the backend's address, and the app degrades to a clear 503 rather than
 * an opaque CORS failure when the simulation isn't running.
 */

const BACKEND =
  process.env.AETHER_BACKEND_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

const READ_PATHS = new Set([
  "health",
  "state",
  "portfolio",
  "companies",
  "prices",
  "events",
  "missions",
]);

const WRITE_PATHS = new Set(["advance", "trade", "reset"]);

function unreachable(error: unknown) {
  return NextResponse.json(
    {
      error:
        "The simulation backend is not reachable. Start it with: python3 backend/aether_backend_v4.py --server --port 8000",
      detail: error instanceof Error ? error.message : String(error),
    },
    { status: 503 },
  );
}

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const endpoint = path.join("/");

  if (!READ_PATHS.has(endpoint)) {
    return NextResponse.json({ error: "unknown endpoint" }, { status: 404 });
  }

  try {
    const upstream = await fetch(`${BACKEND}/${endpoint}`, {
      cache: "no-store",
    });
    const body = await upstream.json();
    return NextResponse.json(body, { status: upstream.status });
  } catch (error) {
    return unreachable(error);
  }
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const endpoint = path.join("/");

  if (!WRITE_PATHS.has(endpoint)) {
    return NextResponse.json({ error: "unknown endpoint" }, { status: 404 });
  }

  let payload: unknown = {};
  try {
    payload = await request.json();
  } catch {
    payload = {};
  }

  try {
    const upstream = await fetch(`${BACKEND}/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    const body = await upstream.json();
    return NextResponse.json(body, { status: upstream.status });
  } catch (error) {
    return unreachable(error);
  }
}

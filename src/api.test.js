import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { createContext, SourceTextModule } from "node:vm";

const source = await readFile(new URL("./api.js", import.meta.url), "utf8");

async function client(responses) {
  const calls = [];
  const events = [];
  const module = new SourceTextModule(source, {
    context: createContext({
      Event,
      window: {
        location: { protocol: "http:", hostname: "localhost", origin: "http://localhost:5173" },
        dispatchEvent: (event) => events.push(event.type),
      },
      fetch: async (url, options) => {
        calls.push({ url, ...options });
        assert.ok(responses.length, "Unexpected API call");
        const [status, data] = responses.shift();
        return { ok: status < 400, status, json: async () => data };
      },
    }),
    initializeImportMeta: (meta) => { meta.env = { DEV: true }; },
  });
  await module.link(() => {});
  await module.evaluate();
  return { api: module.namespace.api, calls, events };
}

test("concurrent bootstrap and mutation share one session and use rotated login CSRF", async () => {
  const { api, calls } = await client([
    [200, { user: null, csrf_token: "anonymous" }],
    [200, { user: { id: "learner" }, csrf_token: "signed-in" }],
    [200, { ok: true }],
  ]);
  await Promise.all([api("/auth/me"), api("/auth/me"), api("/auth/login", { email: "test@example.com", password: "password" })]);
  await api("/me/onboarding", { goal: "Learn", experience: "beginner" });
  assert.equal(calls.length, 3);
  assert.equal(calls[1].headers["X-CSRF-Token"], "anonymous");
  assert.equal(calls[2].headers["X-CSRF-Token"], "signed-in");
  assert.ok(calls.every((call) => call.credentials === "include"));
});

test("expired CSRF refreshes the session without replaying a mutation", async () => {
  const { api, calls, events } = await client([
    [200, { user: { id: "learner" }, csrf_token: "old" }],
    [403, { detail: "Invalid or expired CSRF token; reload your session" }],
    [200, { user: null, csrf_token: "fresh" }],
    [200, { user: { id: "learner" }, csrf_token: "authenticated" }],
  ]);
  await assert.rejects(api("/simulation/trade", { qty: 1 }), /session was refreshed/);
  assert.equal(calls.filter((call) => call.method === "POST").length, 1);
  assert.deepEqual(events, ["session-expired"]);
  await api("/auth/login", { email: "test@example.com", password: "password" });
  assert.equal(calls[3].headers["X-CSRF-Token"], "fresh");
});

test("credential failures do not sign out a valid session", async () => {
  const { api, events } = await client([
    [200, { user: { id: "learner" }, csrf_token: "valid" }],
    [401, { detail: "Invalid password" }],
    [401, { detail: "Sign in to continue" }],
  ]);
  await assert.rejects(api("/me/delete", { password: "wrong" }), /Invalid password/);
  assert.deepEqual(events, []);
  await assert.rejects(api("/me/onboarding", {}), /Sign in to continue/);
  assert.deepEqual(events, ["session-expired"]);
});

test("logout clears CSRF so the next mutation bootstraps again", async () => {
  const { api, calls } = await client([
    [200, { csrf_token: "signed-in" }],
    [200, { ok: true }],
    [200, { csrf_token: "anonymous" }],
    [200, { ok: true }],
  ]);
  await api("/auth/logout", {});
  await api("/auth/forgot-password", { email: "test@example.com" });
  assert.equal(calls[2].url, "/api/auth/me");
  assert.equal(calls[3].headers["X-CSRF-Token"], "anonymous");
});

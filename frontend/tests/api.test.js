import assert from "node:assert/strict";
import { test } from "node:test";
import { api, ApiError, requestId, setAccessToken } from "../src/api.js";

test("registration sends required email and password and returns the session", async (t) => {
  const body = { firstName: "Test", lastName: "Runner", email: "test@example.com", password: "TestPassword123" };
  const session = { accessToken: "new-token", user: { userId: "athlete" } };
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url, "/api/users");
    assert.equal(options.method, "POST");
    assert.deepEqual(JSON.parse(options.body), body);
    return Response.json(session, { status: 201 });
  });
  assert.deepEqual(await api.register(body), session);
});

test("dashboard reads forward cancellation and query parameters", async (t) => {
  const controller = new AbortController();
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url, "/api/users/athlete/dashboard?days=90");
    assert.equal(options.signal, controller.signal);
    return Response.json({ windowDays: 90 });
  });
  assert.deepEqual(await api.dashboard("athlete", 90, { signal: controller.signal }), { windowDays: 90 });
});

test("API errors preserve code, field details and conflict metadata", async (t) => {
  t.mock.method(globalThis, "fetch", async () => Response.json({
    error: { code: "DUPLICATE_USER", message: "Already registered", existingUserId: "existing",
      details: [{ field: "firstName", message: "duplicate" }] },
  }, { status: 409 }));
  await assert.rejects(api.register({ firstName: "A", lastName: "B" }), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 409);
    assert.equal(error.code, "DUPLICATE_USER");
    assert.equal(error.extra.existingUserId, "existing");
    assert.equal(error.details[0].field, "firstName");
    return true;
  });
});

test("network failures are explicitly reported", async (t) => {
  t.mock.method(globalThis, "fetch", async () => { throw new TypeError("offline"); });
  await assert.rejects(api.users(), { code: "NETWORK", status: 0 });
});

test("intentional aborts are not mislabeled as network errors", async (t) => {
  const controller = new AbortController();
  const error = new DOMException("cancelled", "AbortError");
  controller.abort();
  t.mock.method(globalThis, "fetch", async () => { throw error; });
  await assert.rejects(api.users({ signal: controller.signal }), (caught) => caught === error);
});

test("invalid successful responses are surfaced instead of returning null", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response("<html>proxy failure</html>"));
  await assert.rejects(api.users(), { code: "INVALID_RESPONSE" });
});

test("activity POST preserves its idempotency key and body", async (t) => {
  const body = { userId: "athlete", sport: "walking", metricType: "distance", value: 1.55,
    clientRequestId: requestId() };
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url, "/api/activities");
    assert.equal(options.method, "POST");
    assert.deepEqual(JSON.parse(options.body), body);
    return Response.json({ points: 77 });
  });
  assert.deepEqual(await api.logActivity(body), { points: 77 });
});

test("private requests include a bearer token", async (t) => {
  t.after(() => setAccessToken(null));
  setAccessToken("test-access-token");
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url, "/api/auth/me");
    assert.equal(options.headers.Authorization, "Bearer test-access-token");
    return Response.json({ userId: "athlete" });
  });
  assert.deepEqual(await api.me(), { userId: "athlete" });
});

test("expired tokens are cleared after an unauthorized response", async (t) => {
  t.after(() => setAccessToken(null));
  setAccessToken("expired-token");
  let calls = 0;
  t.mock.method(globalThis, "fetch", async (url, options) => {
    calls += 1;
    if (calls === 1) {
      assert.equal(url, "/api/auth/me");
      assert.equal(options.headers.Authorization, "Bearer expired-token");
      return Response.json({ error: { code: "UNAUTHORIZED", message: "Expired" } }, { status: 401 });
    }
    assert.equal(url, "/api/leaderboard?trendDays=7");
    assert.equal(options.headers.Authorization, undefined);
    return Response.json({ entries: [] });
  });
  await assert.rejects(api.me(), { status: 401 });
  assert.deepEqual(await api.leaderboard(), { entries: [] });
});

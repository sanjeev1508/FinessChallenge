import assert from "node:assert/strict";
import { test } from "node:test";
import { createLatestRequest } from "../src/latestRequest.js";

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test("only the newest response is published, even if abort is ignored", async () => {
  const first = deferred(), second = deferred(), seen = [], signals = [];
  const queue = [first, second];
  const runner = createLatestRequest((signal) => {
    signals.push(signal);
    return queue.shift().promise;
  }, (data) => seen.push(data), assert.fail);
  const old = runner.run(), latest = runner.run();
  assert.equal(signals[0].aborted, true);
  second.resolve("90-day dashboard");
  await latest;
  first.resolve("14-day dashboard");
  await old;
  assert.deepEqual(seen, ["90-day dashboard"]);
});

test("stale errors cannot replace current data", async () => {
  const first = deferred(), second = deferred(), errors = [], seen = [];
  const queue = [first, second];
  const runner = createLatestRequest(() => queue.shift().promise,
    (data) => seen.push(data), (error) => errors.push(error));
  const old = runner.run(), latest = runner.run();
  second.resolve("current athlete");
  await latest;
  first.reject(new Error("old athlete not found"));
  await old;
  assert.deepEqual(seen, ["current athlete"]);
  assert.deepEqual(errors, []);
});

test("cancel prevents updates after unmount", async () => {
  const pending = deferred();
  const runner = createLatestRequest(() => pending.promise, assert.fail, assert.fail);
  const work = runner.run();
  runner.cancel();
  pending.resolve("unmounted");
  await work;
});

test("current request failures are surfaced and can be retried", async () => {
  const error = new Error("network unavailable"), errors = [], seen = [];
  let attempt = 0;
  const runner = createLatestRequest(async () => {
    if (attempt++ === 0) throw error;
    return "recovered";
  }, (data) => seen.push(data), (failure) => errors.push(failure));
  await runner.run();
  await runner.run();
  assert.deepEqual(errors, [error]);
  assert.deepEqual(seen, ["recovered"]);
});

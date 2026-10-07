import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { test } from "node:test";

const output = new URL("../../backend/app/static/", import.meta.url);
const assets = new URL("assets/", output);

test("production JavaScript chunks stay below 500 kB", () => {
  const chunks = readdirSync(assets).filter((name) => name.endsWith(".js"));
  assert.ok(chunks.length >= 2, "dashboard must be a separate chunk");
  for (const name of chunks) {
    assert.ok(statSync(new URL(name, assets)).size < 500_000, `${name} exceeds 500 kB`);
  }
});

test("initial page bundle stays below 250 kB with a lazy dashboard", () => {
  const html = readFileSync(new URL("index.html", output), "utf8");
  const src = html.match(/src="([^"]+\.js)"/)?.[1];
  assert.ok(src, "index.html must reference the built entry script");
  const entry = new URL(src, output);
  assert.ok(statSync(entry).size < 250_000, "charts must not inflate the initial bundle");
  assert.match(readFileSync(entry, "utf8"), /import\(["']\.\/Dashboard-/);
});

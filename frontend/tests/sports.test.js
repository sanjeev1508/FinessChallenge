import assert from "node:assert/strict";
import { test } from "node:test";
import { previewPoints } from "../src/sports.js";

for (const [sport, input, expected] of [
  ["running", { km: "0.29" }, 29],
  ["walking", { km: "1.55" }, 77],
  ["cycling", { km: "1.039" }, 25],
  ["cycling", { km: "0.039" }, 0],
  ["swimming", { minutes: "1", seconds: "55" }, 15],
  ["gym", { minutes: "45", seconds: "30" }, 225],
  ["gym", { minutes: "", seconds: "59" }, 0],
  ["steps", { steps: "399" }, 3],
  ["steps", { steps: "99" }, 0],
]) {
  test(`${sport} preview floors ${JSON.stringify(input)} to ${expected}`, () => {
    assert.equal(previewPoints(sport, input), expected);
  });
}

for (const [sport, input] of [
  ["running", { km: "0.0099" }],
  ["running", { km: "Infinity" }],
  ["running", { km: "-1" }],
  ["running", { km: "1001" }],
  ["gym", { minutes: "-1", seconds: "0" }],
  ["gym", { minutes: "1.5", seconds: "0" }],
  ["swimming", { minutes: "1", seconds: "60" }],
  ["swimming", { minutes: "1440", seconds: "1" }],
  ["steps", { steps: "200001" }],
  ["steps", { steps: "100.5" }],
]) {
  test(`${sport} preview does not award invalid ${JSON.stringify(input)}`, () => {
    assert.equal(previewPoints(sport, input), 0);
  });
}

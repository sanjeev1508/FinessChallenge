import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDate, todayISO } from "../src/calendar.js";

test("calendar defaults use the UTC date across midnight offsets", () => {
  assert.equal(todayISO(new Date("2026-10-08T01:00:00+05:30")), "2026-10-07");
  assert.equal(todayISO(new Date("2026-10-07T23:00:00-07:00")), "2026-10-08");
});

test("date-only labels are formatted in UTC, never shifted by local timezone", () => {
  const options = { day: "numeric", month: "short", year: "numeric" };
  const expected = new Date("2026-10-07T00:00:00Z").toLocaleDateString(undefined, { ...options, timeZone: "UTC" });
  assert.equal(formatDate("2026-10-07", options), expected);
  assert.equal(formatDate("2026-10-07", { ...options, timeZone: "America/Los_Angeles" }), expected);
});

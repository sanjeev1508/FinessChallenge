"""Scoring & normalisation.

All arithmetic is done on integers (metres, seconds, steps) so that flooring is
exact. Using floats would be wrong: 0.29 km * 100 in binary floating point is
28.999999999999996, which floors to 28 instead of 29.
"""
import re
from decimal import Decimal, InvalidOperation

SPORT_METRIC: dict[str, str] = {
    "running": "distance",
    "walking": "distance",
    "cycling": "distance",
    "swimming": "duration",
    "gym": "duration",
    "steps": "count",
}

# Points per unit: per km (distance), per full minute (duration), per full 100 steps (count)
POINTS_PER_KM = {"running": 100, "walking": 50, "cycling": 25}
POINTS_PER_MINUTE = {"swimming": 15, "gym": 5}
STEPS_PER_BLOCK = 100
POINTS_PER_STEP_BLOCK = 1

DURATION_RE = re.compile(r"^(\d{1,4}):([0-5]\d)$")


class ScoringError(ValueError):
    pass


# ---------- conversions of raw input -> exact integer units ----------

def km_to_metres(km: int | float | str | Decimal) -> int:
    """Convert a km value (max 3 decimal places, i.e. metre precision) to metres."""
    try:
        d = Decimal(str(km))
    except InvalidOperation as exc:
        raise ScoringError("distance must be a number") from exc
    if not d.is_finite():
        raise ScoringError("distance must be a finite number")
    metres = d * 1000
    if metres != metres.to_integral_value():
        raise ScoringError("distance supports at most 3 decimal places (metre precision)")
    return int(metres)


def parse_duration(value: str) -> int:
    """'mm:ss' -> total seconds. Minutes may exceed 59 (e.g. '95:30')."""
    m = DURATION_RE.match(value.strip())
    if not m:
        raise ScoringError("duration must be in 'min:sec' format, e.g. '45:30' (seconds 00-59)")
    return int(m.group(1)) * 60 + int(m.group(2))


# ---------- points ----------

def distance_points(sport: str, distance_m: int) -> int:
    # floor(km * rate) == floor(metres * rate / 1000), done in integers
    return (distance_m * POINTS_PER_KM[sport]) // 1000


def duration_points(sport: str, duration_s: int) -> int:
    full_minutes = duration_s // 60          # only completed minutes count
    return full_minutes * POINTS_PER_MINUTE[sport]


def steps_points(steps: int) -> int:
    full_blocks = steps // STEPS_PER_BLOCK   # 399 -> 3 blocks
    return full_blocks * POINTS_PER_STEP_BLOCK


def calculate_points(sport: str, *, distance_m: int | None = None,
                     duration_s: int | None = None, steps: int | None = None) -> int:
    metric = SPORT_METRIC.get(sport)
    if metric == "distance" and distance_m is not None:
        return distance_points(sport, distance_m)
    if metric == "duration" and duration_s is not None:
        return duration_points(sport, duration_s)
    if metric == "count" and steps is not None:
        return steps_points(steps)
    raise ScoringError(f"no valid metric supplied for sport '{sport}'")


def scoring_rules() -> list[dict]:
    """Human-readable rules (served to the frontend so it never hard-codes them)."""
    rules = []
    for sport, rate in POINTS_PER_KM.items():
        rules.append({"sport": sport, "metricType": "distance", "unit": "km", "per": 1, "points": rate,
                      "rounding": "points floored to an integer"})
    for sport, rate in POINTS_PER_MINUTE.items():
        rules.append({"sport": sport, "metricType": "duration", "unit": "minute", "per": 1, "points": rate,
                      "rounding": "only fully completed minutes count"})
    rules.append({"sport": "steps", "metricType": "count", "unit": "steps", "per": STEPS_PER_BLOCK,
                  "points": POINTS_PER_STEP_BLOCK, "rounding": "only full blocks of 100 steps count"})
    return rules

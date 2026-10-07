import pytest

from app.scoring import (ScoringError, distance_points, duration_points, km_to_metres,
                         parse_duration, steps_points)


@pytest.mark.parametrize("sport,km,expected", [
    ("walking", 1.55, 77),      # spec example: 77.5 -> 77
    ("running", 1, 100),
    ("running", 0.29, 29),      # float trap: 0.29*100 = 28.999999999999996
    ("running", 0.999, 99),
    ("cycling", 1.039, 25),     # 25.975 -> 25
    ("cycling", 0.039, 0),      # < 1 point -> 0
    ("walking", 42.195, 2109),  # 2109.75 -> 2109
])
def test_distance(sport, km, expected):
    assert distance_points(sport, km_to_metres(km)) == expected


@pytest.mark.parametrize("sport,dur,expected", [
    ("swimming", "1:55", 15),   # spec example: counts as 1 minute
    ("gym", "0:59", 0),
    ("gym", "60:00", 300),
    ("swimming", "90:30", 1350),
])
def test_duration(sport, dur, expected):
    assert duration_points(sport, parse_duration(dur)) == expected


@pytest.mark.parametrize("steps,expected", [(399, 3), (99, 0), (100, 1), (10_050, 100)])
def test_steps(steps, expected):
    assert steps_points(steps) == expected


@pytest.mark.parametrize("bad", ["1:60", "abc", "1:5", ":30", "-1:00", "1:00:00"])
def test_bad_duration(bad):
    with pytest.raises(ScoringError):
        parse_duration(bad)


def test_distance_precision_limit():
    with pytest.raises(ScoringError):
        km_to_metres(1.0001)

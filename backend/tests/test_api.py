import threading
from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.database import SessionLocal
from app.models import Activity, User, utc_today


# ------------------------------------------------------------ registration

def test_register_returns_user_id(client):
    r = client.post("/api/users", json={"firstName": "Priya", "lastName": "Raman", "email": "P@X.com"})
    assert r.status_code == 201
    body = r.json()
    assert len(body["userId"]) == 36 and body["email"] == "p@x.com"


def test_duplicate_names_rejected_case_and_space_insensitive(client):
    first = client.post("/api/users", json={"firstName": "Priya", "lastName": "Raman"}).json()
    r = client.post("/api/users", json={"firstName": "  PRIYA ", "lastName": "raman"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "DUPLICATE_USER"
    assert r.json()["error"]["existingUserId"] == first["userId"]


def test_same_first_name_different_last_name_ok(client):
    assert client.post("/api/users", json={"firstName": "Priya", "lastName": "Raman"}).status_code == 201
    assert client.post("/api/users", json={"firstName": "Priya", "lastName": "Iyer"}).status_code == 201


def test_register_validation(client):
    for body in [{}, {"firstName": "A"}, {"firstName": "", "lastName": "B"}, {"firstName": "R2D2", "lastName": "X"},
                 {"firstName": "A", "lastName": "B", "extra": 1}, {"firstName": 5, "lastName": "B"},
                 {"firstName": "A", "lastName": "B", "email": "nope"}]:
        r = client.post("/api/users", json=body)
        assert r.status_code == 400, body
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_json(client):
    r = client.post("/api/users", content="{bad json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_JSON"


def test_concurrent_duplicate_registration_only_one_wins(client):
    results = []

    def go():
        results.append(client.post("/api/users", json={"firstName": "Race", "lastName": "Condition"}).status_code)

    threads = [threading.Thread(target=go) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [201] + [409] * 9


# --------------------------------------------------------------- ingestion

def post(client, uid, sport, metric, value, **kw):
    return client.post("/api/activities", json={"userId": uid, "sport": sport, "metricType": metric,
                                                "value": value, **kw})


def test_ingest_each_sport(client, user_id):
    cases = [("running", "distance", 5.25, 525), ("walking", "distance", 1.55, 77),
             ("cycling", "distance", 20, 500), ("swimming", "duration", "1:55", 15),
             ("gym", "duration", "45:30", 225), ("steps", "count", 399, 3)]
    for sport, metric, value, pts in cases:
        r = post(client, user_id, sport, metric, value, activityDate=str(utc_today() - timedelta(days=1)))
        assert r.status_code == 201, r.json()
        assert r.json()["points"] == pts
    assert client.get(f"/api/users/{user_id}").json()["totalPoints"] == sum(c[3] for c in cases)


def test_mismatch_returns_400(client, user_id):
    for sport, metric in [("running", "duration"), ("gym", "distance"), ("steps", "distance"), ("swimming", "count")]:
        r = post(client, user_id, sport, metric, 1)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "SPORT_METRIC_MISMATCH"


def test_wrong_value_types_return_400(client, user_id):
    bad = [("running", "distance", "5"), ("running", "distance", -1), ("running", "distance", 0),
           ("running", "distance", 1.0001), ("running", "distance", 5000), ("running", "distance", True),
           ("gym", "duration", 30), ("gym", "duration", "30:75"), ("gym", "duration", "0:00"),
           ("steps", "count", 10.5), ("steps", "count", "100"), ("steps", "count", 999_999),
           ("yoga", "duration", "10:00")]
    for sport, metric, value in bad:
        r = post(client, user_id, sport, metric, value)
        assert r.status_code == 400, (sport, metric, value, r.json())


def test_nan_rejected(client, user_id):
    r = client.post("/api/activities", headers={"Content-Type": "application/json"},
                    content=f'{{"userId":"{user_id}","sport":"running","metricType":"distance","value":NaN}}')
    assert r.status_code == 400


def test_bad_user_and_dates(client, user_id):
    assert post(client, "not-a-uuid", "running", "distance", 1).status_code == 400
    r = post(client, "00000000-0000-0000-0000-000000000000", "running", "distance", 1)
    assert r.status_code == 404 and r.json()["error"]["code"] == "USER_NOT_FOUND"
    assert post(client, user_id, "running", "distance", 1,
                activityDate=str(utc_today() + timedelta(days=1))).status_code == 400


def test_one_steps_entry_per_day(client, user_id):
    assert post(client, user_id, "steps", "count", 5000).status_code == 201
    r = post(client, user_id, "steps", "count", 3000)
    assert r.status_code == 409 and r.json()["error"]["code"] == "DAILY_STEPS_EXISTS"


def test_idempotency_key(client, user_id):
    a = post(client, user_id, "running", "distance", 3, clientRequestId="abc-1")
    b = post(client, user_id, "running", "distance", 3, clientRequestId="abc-1")
    assert a.status_code == 201 and b.status_code == 200
    assert b.headers["Idempotent-Replay"] == "true"
    assert a.json()["activityId"] == b.json()["activityId"]
    assert client.get(f"/api/users/{user_id}").json()["totalPoints"] == 300


@pytest.mark.parametrize("changed", [
    {"value": 5},
    {"sport": "walking"},
    {"activityDate": str(utc_today() - timedelta(days=1))},
    {"notes": "Different workout"},
])
def test_idempotency_rejects_changed_payload(client, user_id, changed):
    body = {"userId": user_id, "sport": "running", "metricType": "distance",
            "value": 1, "clientRequestId": "same-key"}
    assert client.post("/api/activities", json=body).status_code == 201
    r = client.post("/api/activities", json={**body, **changed})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert "Idempotent-Replay" not in r.headers
    user = client.get(f"/api/users/{user_id}").json()
    assert user["totalPoints"] == 100 and user["activityCount"] == 1


def test_idempotency_compares_normalized_values(client, user_id):
    a = post(client, user_id, "gym", "duration", "01:55", notes=" workout ", clientRequestId="normalized")
    b = post(client, user_id, "gym", "duration", "1:55", notes="workout", clientRequestId="normalized")
    assert a.status_code == 201 and b.status_code == 200
    assert a.json()["activityId"] == b.json()["activityId"]


def test_concurrent_idempotency_conflict(client, user_id):
    results = []

    def go(value):
        results.append(post(client, user_id, "running", "distance", value,
                            clientRequestId="race-key"))

    threads = [threading.Thread(target=go, args=(value,)) for value in [1, 5]]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(r.status_code for r in results) == [201, 409]
    accepted = next(r.json() for r in results if r.status_code == 201)
    assert client.get(f"/api/users/{user_id}").json()["totalPoints"] == accepted["points"]


def test_concurrent_ingestion_totals_consistent(client, user_id):
    def go():
        for _ in range(10):
            assert post(client, user_id, "running", "distance", 1).status_code == 201

    threads = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert client.get(f"/api/users/{user_id}").json()["totalPoints"] == 80 * 100


# ---------------------------------------------------- leaderboard/dashboard

def test_leaderboard_ranking_ties_and_trend(client):
    ids = {}
    for name in ["Ann", "Bob", "Cat"]:
        ids[name] = client.post("/api/users", json={"firstName": name, "lastName": "Test"}).json()["userId"]
    old = str(utc_today() - timedelta(days=10))
    activity = post(client, ids["Ann"], "running", "distance", 5, activityDate=old).json()
    with SessionLocal() as db:
        timestamp = datetime.combine(date.fromisoformat(old), time.min, tzinfo=timezone.utc)
        db.get(User, ids["Ann"]).created_at = timestamp
        db.get(Activity, activity["activityId"]).created_at = timestamp
        db.commit()
    post(client, ids["Bob"], "running", "distance", 6)                     # Bob overtakes today
    post(client, ids["Cat"], "running", "distance", 6)                     # tie with Bob
    board = client.get("/api/leaderboard").json()["entries"]
    ranks = {e["firstName"]: e for e in board}
    assert ranks["Bob"]["rank"] == ranks["Cat"]["rank"] == 1
    assert ranks["Ann"]["rank"] == 3
    assert ranks["Ann"]["trend"] == "down" and ranks["Ann"]["rankChange"] == -2
    assert ranks["Bob"]["trend"] == "new"  # registered after the comparison date


def test_backdated_submission_does_not_rewrite_previous_rank(client, user_id):
    old = utc_today() - timedelta(days=10)
    with SessionLocal() as db:
        db.get(User, user_id).created_at = datetime.combine(old, time.min, tzinfo=timezone.utc)
        db.commit()
    before = client.get("/api/leaderboard").json()["entries"][0]
    post(client, user_id, "running", "distance", 5, activityDate=str(old))
    after = client.get("/api/leaderboard").json()["entries"][0]
    assert after["previousRank"] == before["previousRank"]
    assert after["pointsInPeriod"] == 500
    assert after["trend"] == "same"


def test_historical_standings_exclude_next_day_midnight(client, user_id):
    cutoff = utc_today() - timedelta(days=7)
    a = post(client, user_id, "running", "distance", 1).json()
    b = post(client, user_id, "running", "distance", 2).json()
    boundary = datetime.combine(cutoff + timedelta(days=1), time.min, tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.get(User, user_id).created_at = boundary - timedelta(days=1)
        db.get(Activity, a["activityId"]).created_at = boundary - timedelta(microseconds=1)
        db.get(Activity, b["activityId"]).created_at = boundary
        db.commit()
    entry = client.get("/api/leaderboard").json()["entries"][0]
    assert entry["previousRank"] == 1
    assert entry["totalPoints"] == 300
    assert entry["pointsInPeriod"] == 200


def test_dashboard(client, user_id):
    post(client, user_id, "running", "distance", 5)
    post(client, user_id, "gym", "duration", "30:00")
    d = client.get(f"/api/users/{user_id}/dashboard?days=14").json()
    assert d["summary"]["totalPoints"] == 650
    assert d["summary"]["favouriteSport"] == "running"
    assert len(d["timeline"]) == 14 and d["timeline"][-1]["points"] == 650
    assert d["cumulative"][-1]["points"] == 650
    post(client, user_id, "steps", "count", 1234)
    last = client.get(f"/api/users/{user_id}/dashboard?days=14").json()["timeline"][-1]
    assert last["steps"] == 12 and last["stepCount"] == 1234  # sport points vs volume never collide


def test_dashboard_preserves_seconds_without_changing_points(client, user_id):
    for sport, value, points in [("gym", "1:55", 5), ("gym", "0:59", 0), ("swimming", "0:30", 0)]:
        assert post(client, user_id, sport, "duration", value).json()["points"] == points
    d = client.get(f"/api/users/{user_id}/dashboard").json()
    sports = {s["sport"]: s for s in d["bySport"]}
    assert sports["gym"]["durationSeconds"] == 174
    assert sports["gym"]["durationMinutes"] == pytest.approx(174 / 60)
    assert sports["swimming"]["durationSeconds"] == 30
    assert sports["swimming"]["durationMinutes"] == 0.5
    assert d["timeline"][-1]["durationSeconds"] == 204
    assert d["timeline"][-1]["durationMinutes"] == pytest.approx(204 / 60)
    assert d["summary"]["totalPoints"] == 5


def test_utc_day_controls_defaults_validation_and_windows(client, user_id, monkeypatch):
    from app import models

    now = datetime(2026, 10, 7, 23, 59, 59, tzinfo=timezone.utc)
    monkeypatch.setattr(models, "utcnow", lambda: now)
    activity = post(client, user_id, "steps", "count", 100)
    assert activity.json()["activityDate"] == "2026-10-07"
    assert post(client, user_id, "running", "distance", 1, activityDate="2026-10-08").status_code == 400
    assert client.get("/api/leaderboard").json()["comparedTo"] == "2026-09-30"
    d = client.get(f"/api/users/{user_id}/dashboard").json()
    assert d["timeline"][-1]["date"] == "2026-10-07"
    assert d["summary"]["currentStreakDays"] == 1
    now += timedelta(seconds=1)
    assert post(client, user_id, "steps", "count", 200).status_code == 201
    d = client.get(f"/api/users/{user_id}/dashboard").json()
    assert d["timeline"][-1]["date"] == "2026-10-08"
    assert d["summary"]["currentStreakDays"] == 2


def test_unknown_api_route_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"

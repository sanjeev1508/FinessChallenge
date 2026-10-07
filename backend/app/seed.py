"""Deterministic demo data so the app is populated on first launch."""
import random
from datetime import date, datetime, time, timedelta, timezone

from .schemas import ActivityCreate, UserCreate
from . import services

DEMO_USERS = [("Priya", "Raman"), ("Arjun", "Mehta"), ("Kavya", "Iyer"), ("Rahul", "Nair"),
              ("Sneha", "Kulkarni"), ("Vikram", "Singh"), ("Ananya", "Das"), ("Karthik", "Subramanian")]

# Each person has a favourite sport so the dashboards look different.
PROFILES = {
    "Priya": ["running", "running", "steps", "gym"],
    "Arjun": ["cycling", "cycling", "steps", "running"],
    "Kavya": ["swimming", "swimming", "walking", "steps"],
    "Rahul": ["gym", "gym", "steps", "walking"],
    "Sneha": ["walking", "steps", "steps", "running"],
    "Vikram": ["running", "cycling", "gym", "steps"],
    "Ananya": ["steps", "walking", "swimming"],
    "Karthik": ["cycling", "running", "swimming", "steps"],
}


def _value(rng: random.Random, sport: str):
    if sport == "running":
        return round(rng.uniform(2, 12), 2)
    if sport == "walking":
        return round(rng.uniform(1.5, 8), 2)
    if sport == "cycling":
        return round(rng.uniform(6, 28), 1)
    if sport in ("swimming", "gym"):
        lo, hi = (15, 60) if sport == "swimming" else (25, 90)
        return f"{rng.randint(lo, hi)}:{rng.randint(0, 59):02d}"
    return rng.randint(3000, 16000)


def seed_demo(db) -> None:
    if services.list_users(db):
        return
    rng = random.Random(42)
    today = date.today()
    for first, last in DEMO_USERS:
        user = services.register_user(db, UserCreate(firstName=first, lastName=last))
        user.created_at = datetime.combine(today - timedelta(days=35), time.min, tzinfo=timezone.utc)
        db.commit()
        activity_rate = rng.uniform(0.45, 0.85)
        for offset in range(34, -1, -1):
            day = today - timedelta(days=offset)
            if rng.random() > activity_rate:
                continue
            sports = sorted(set(rng.sample(PROFILES[first], k=rng.choice([1, 1, 2]))))
            for sport in sports:
                metric = {"running": "distance", "walking": "distance", "cycling": "distance",
                          "swimming": "duration", "gym": "duration", "steps": "count"}[sport]
                activity, _ = services.create_activity(db, ActivityCreate(
                    userId=user.id, sport=sport, metricType=metric,
                    value=_value(rng, sport), activityDate=day))
                # Demo records simulate submissions on their workout day.
                activity.created_at = datetime.combine(day, time.min, tzinfo=timezone.utc)
                user.leaderboard.last_activity_at = activity.created_at
                user.leaderboard.updated_at = activity.created_at
                db.commit()

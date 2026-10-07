"""Business logic. Routers stay thin; everything transactional lives here."""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .errors import ApiError
from .models import SPORTS, Activity, LeaderboardEntry, User, utc_today, utcnow
from .schemas import ActivityCreate, UserCreate, normalise_name
from .scoring import calculate_points
from datetime import datetime, time, timezone


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on read; all stored timestamps are UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ------------------------------------------------------------------ users

def user_to_dict(user: User) -> dict:
    lb = user.leaderboard
    return {
        "userId": user.id, "firstName": user.first_name, "lastName": user.last_name,
        "email": user.email, "createdAt": as_utc(user.created_at),
        "totalPoints": lb.total_points if lb else 0,
        "activityCount": lb.activity_count if lb else 0,
    }


def _find_by_name(db: Session, first_key: str, last_key: str) -> User | None:
    return db.scalar(select(User).where(User.first_name_key == first_key, User.last_name_key == last_key))


def register_user(db: Session, data: UserCreate) -> User:
    first_key, last_key = normalise_name(data.firstName), normalise_name(data.lastName)
    # Fast path gives a friendly error; the UNIQUE constraint is the real guarantee.
    existing = _find_by_name(db, first_key, last_key)
    if existing:
        raise _duplicate(existing)
    user = User(first_name=data.firstName, last_name=data.lastName, email=data.email,
                first_name_key=first_key, last_name_key=last_key)
    user.leaderboard = LeaderboardEntry(total_points=0, activity_count=0)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent identical registration.
        db.rollback()
        existing = _find_by_name(db, first_key, last_key)
        if existing:
            raise _duplicate(existing)
        raise
    return user


def _duplicate(existing: User) -> ApiError:
    return ApiError(409, "DUPLICATE_USER",
                    f"A user named {existing.first_name} {existing.last_name} is already registered.",
                    {"existingUserId": existing.id})


def get_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if not user:
        raise ApiError(404, "USER_NOT_FOUND", f"No user with id {user_id}.")
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.first_name_key, User.last_name_key)))


# ------------------------------------------------------------- activities

def activity_to_dict(a: Activity) -> dict:
    if a.metric_type == "distance":
        value = a.distance_m / 1000
        normalized = {"distanceKm": a.distance_m / 1000, "distanceMetres": a.distance_m}
    elif a.metric_type == "duration":
        value = a.raw_value
        normalized = {"durationSeconds": a.duration_s, "countedMinutes": a.duration_s // 60}
    else:
        value = a.steps
        normalized = {"steps": a.steps, "countedSteps": (a.steps // 100) * 100}
    return {"activityId": a.id, "userId": a.user_id, "sport": a.sport, "metricType": a.metric_type,
            "value": value, "normalized": normalized, "points": a.points,
            "activityDate": a.activity_date, "notes": a.notes, "createdAt": as_utc(a.created_at)}


def _find_replay(db: Session, user_id: str, key: str | None) -> Activity | None:
    if not key:
        return None
    return db.scalar(select(Activity).where(Activity.user_id == user_id, Activity.client_request_id == key))


def _validate_replay(activity: Activity, data: ActivityCreate) -> None:
    n = data.normalized
    if (activity.sport != data.sport or activity.metric_type != data.metricType
            or activity.distance_m != n["distance_m"] or activity.duration_s != n["duration_s"]
            or activity.steps != n["steps"]
            or (data.activityDate is not None and activity.activity_date != data.activityDate)
            or activity.notes != ((data.notes or "").strip() or None)):
        raise ApiError(409, "IDEMPOTENCY_CONFLICT",
                       "This clientRequestId was already used for a different activity. "
                       "Use a new key for a new submission.")


def _steps_conflict(db: Session, user_id: str, day: date) -> Activity | None:
    return db.scalar(select(Activity).where(Activity.user_id == user_id, Activity.sport == "steps",
                                            Activity.activity_date == day))


def create_activity(db: Session, data: ActivityCreate) -> tuple[Activity, bool]:
    """Returns (activity, replayed). replayed=True when an idempotency key matched."""
    get_user(db, data.userId)
    replay = _find_replay(db, data.userId, data.clientRequestId)
    if replay:
        _validate_replay(replay, data)
        return replay, True

    day = data.activityDate or utc_today()
    if data.sport == "steps" and _steps_conflict(db, data.userId, day):
        raise _steps_error(day)

    n = data.normalized
    points = calculate_points(data.sport, distance_m=n["distance_m"], duration_s=n["duration_s"], steps=n["steps"])
    activity = Activity(
        user_id=data.userId, sport=data.sport, metric_type=data.metricType,
        distance_m=n["distance_m"], duration_s=n["duration_s"], steps=n["steps"],
        raw_value=str(data.value), points=points, activity_date=day,
        notes=(data.notes or "").strip() or None, client_request_id=data.clientRequestId,
    )
    db.add(activity)
    # Atomic increment in the same transaction: the leaderboard can never drift
    # from the activity log, even under concurrent writes.
    db.execute(
        update(LeaderboardEntry)
        .where(LeaderboardEntry.user_id == data.userId)
        .values(total_points=LeaderboardEntry.total_points + points,
                activity_count=LeaderboardEntry.activity_count + 1,
                last_activity_at=utcnow(), updated_at=utcnow())
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        replay = _find_replay(db, data.userId, data.clientRequestId)
        if replay:
            _validate_replay(replay, data)
            return replay, True
        if data.sport == "steps" and _steps_conflict(db, data.userId, day):
            raise _steps_error(day)
        raise
    return activity, False


def _steps_error(day: date) -> ApiError:
    return ApiError(409, "DAILY_STEPS_EXISTS",
                    f"Daily steps for {day.isoformat()} are already recorded. Steps are one entry per day.")


def list_activities(db: Session, user_id: str | None, limit: int) -> list[Activity]:
    q = select(Activity).order_by(Activity.activity_date.desc(), Activity.id.desc()).limit(limit)
    if user_id:
        q = q.where(Activity.user_id == user_id)
    return list(db.scalars(q))


def rebuild_leaderboard(db: Session) -> None:
    """Recompute totals from the activity log (recovery / consistency check)."""
    totals = dict(db.execute(select(Activity.user_id, func.sum(Activity.points)).group_by(Activity.user_id)).all())
    counts = dict(db.execute(select(Activity.user_id, func.count()).group_by(Activity.user_id)).all())
    for entry in db.scalars(select(LeaderboardEntry)):
        entry.total_points = int(totals.get(entry.user_id, 0) or 0)
        entry.activity_count = int(counts.get(entry.user_id, 0) or 0)
    db.commit()


# ------------------------------------------------------------- rankings

def competition_rank(scores: list[tuple[str, int]]) -> dict[str, int]:
    """Standard competition ranking ("1224"): ties share a rank, next rank skips."""
    ordered = sorted(scores, key=lambda s: -s[1])
    ranks, prev_points, prev_rank = {}, None, 0
    for i, (uid, pts) in enumerate(ordered, start=1):
        rank = prev_rank if pts == prev_points else i
        ranks[uid] = rank
        prev_points, prev_rank = pts, rank
    return ranks


def leaderboard(db: Session, trend_days: int = 7, limit: int | None = None) -> dict:
    rows = db.execute(
        select(User, LeaderboardEntry).join(LeaderboardEntry, LeaderboardEntry.user_id == User.id)
    ).all()
    cutoff = utc_today() - timedelta(days=trend_days)
    cutoff_end = datetime.combine(cutoff + timedelta(days=1), time.min, tzinfo=timezone.utc)
    # Submission time preserves the standings even when workouts are backdated.
    prev_totals = dict(db.execute(
        select(Activity.user_id, func.coalesce(func.sum(Activity.points), 0))
        .where(Activity.created_at < cutoff_end).group_by(Activity.user_id)
    ).all())
    # Only users who already existed at the cutoff have a previous rank.
    existed = [(u.id, int(prev_totals.get(u.id, 0))) for u, _ in rows if as_utc(u.created_at) < cutoff_end]
    prev_rank = competition_rank(existed)
    cur_rank = competition_rank([(u.id, lb.total_points) for u, lb in rows])

    entries = []
    for u, lb in rows:
        prev = prev_rank.get(u.id)
        entries.append({
            "rank": cur_rank[u.id],
            "userId": u.id, "firstName": u.first_name, "lastName": u.last_name,
            "totalPoints": lb.total_points, "activityCount": lb.activity_count,
            "pointsInPeriod": lb.total_points - int(prev_totals.get(u.id, 0)),
            "previousRank": prev,
            "rankChange": (prev - cur_rank[u.id]) if prev is not None else None,
            "trend": "new" if prev is None else ("up" if prev > cur_rank[u.id]
                                                 else "down" if prev < cur_rank[u.id] else "same"),
            "lastActivityAt": as_utc(lb.last_activity_at),
        })
    entries.sort(key=lambda e: (e["rank"], e["firstName"].casefold(), e["lastName"].casefold()))
    if limit:
        entries = entries[:limit]
    return {"trendDays": trend_days, "comparedTo": cutoff, "generatedAt": utcnow(),
            "totalUsers": len(rows), "entries": entries}


# ------------------------------------------------------------- dashboard

def dashboard(db: Session, user_id: str, days: int = 30) -> dict:
    user = get_user(db, user_id)
    acts = list(db.scalars(select(Activity).where(Activity.user_id == user_id)
                           .order_by(Activity.activity_date, Activity.id)))
    today = utc_today()
    start = today - timedelta(days=days - 1)

    by_sport = {s: {"sport": s, "points": 0, "count": 0, "distanceKm": 0.0, "durationSeconds": 0, "steps": 0}
                for s in SPORTS}
    timeline = {start + timedelta(days=i): {"date": (start + timedelta(days=i)).isoformat(), "points": 0,
                                            "distanceKm": 0.0, "durationSeconds": 0, "stepCount": 0,
                                            # per-sport points, keyed by sport name
                                            **{s: 0 for s in SPORTS}}
                for i in range(days)}
    active_days = set()
    for a in acts:
        s = by_sport[a.sport]
        s["points"] += a.points
        s["count"] += 1
        s["distanceKm"] += (a.distance_m or 0) / 1000
        s["durationSeconds"] += a.duration_s or 0
        s["steps"] += a.steps or 0
        active_days.add(a.activity_date)
        t = timeline.get(a.activity_date)
        if t is not None:
            t["points"] += a.points
            t[a.sport] += a.points
            t["distanceKm"] += (a.distance_m or 0) / 1000
            t["durationSeconds"] += a.duration_s or 0
            t["stepCount"] += a.steps or 0

    for s in by_sport.values():
        s["distanceKm"] = round(s["distanceKm"], 3)
        s["durationMinutes"] = s["durationSeconds"] / 60
    for t in timeline.values():
        t["distanceKm"] = round(t["distanceKm"], 3)
        t["durationMinutes"] = t["durationSeconds"] / 60

    # Streak: consecutive active days ending today (or yesterday, so it isn't
    # broken before the user has logged today's workout).
    streak, cursor = 0, today if today in active_days else today - timedelta(days=1)
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)

    total = sum(a.points for a in acts)
    board = leaderboard(db)
    me = next((e for e in board["entries"] if e["userId"] == user_id), None)
    favourite = max(by_sport.values(), key=lambda s: s["points"]) if acts else None

    # Cumulative points over the window (starting balance = points before window)
    running_total = sum(a.points for a in acts if a.activity_date < start)
    cumulative = []
    for t in timeline.values():
        running_total += t["points"]
        cumulative.append({"date": t["date"], "points": running_total})

    return {
        "user": user_to_dict(user),
        "summary": {"totalPoints": total, "activityCount": len(acts), "activeDays": len(active_days),
                    "currentStreakDays": streak, "rank": me["rank"] if me else None,
                    "rankChange": me["rankChange"] if me else None, "totalUsers": board["totalUsers"],
                    "favouriteSport": favourite["sport"] if favourite and favourite["points"] > 0 else None,
                    "pointsLast7Days": sum(a.points for a in acts if a.activity_date > today - timedelta(days=7))},
        "bySport": [s for s in by_sport.values()],
        "timeline": list(timeline.values()),
        "cumulative": cumulative,
        "recentActivities": [activity_to_dict(a) for a in reversed(acts[-15:])],
        "windowDays": days,
    }

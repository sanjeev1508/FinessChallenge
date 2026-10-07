"""ORM entities: users, activities and the materialised leaderboard."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (CheckConstraint, Date, DateTime, ForeignKey, Index,
                        Integer, String, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

SPORTS = ("running", "walking", "cycling", "swimming", "gym", "steps")
METRIC_TYPES = ("distance", "duration", "count")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc_today() -> date:
    return utcnow().date()


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # Canonical forms used for duplicate detection ("  JOHN   o'neil " == "john o'neil")
    first_name_key: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name_key: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    activities: Mapped[list["Activity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    leaderboard: Mapped["LeaderboardEntry"] = relationship(back_populates="user", cascade="all, delete-orphan",
                                                           uselist=False)

    __table_args__ = (
        UniqueConstraint("first_name_key", "last_name_key", name="uq_users_full_name"),
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sport: Mapped[str] = mapped_column(String(16), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Exactly one of these is set, matching metric_type (enforced by CHECK below).
    distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)   # metres (exact integer)
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)   # seconds
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_value: Mapped[str] = mapped_column(String(32), nullable=False)       # value exactly as submitted
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(280), nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="activities")

    __table_args__ = (
        CheckConstraint("points >= 0", name="ck_activity_points_non_negative"),
        CheckConstraint(f"sport IN {SPORTS}", name="ck_activity_sport"),
        CheckConstraint(
            "(metric_type = 'distance' AND sport IN ('running','walking','cycling') "
            "   AND distance_m IS NOT NULL AND duration_s IS NULL AND steps IS NULL) OR "
            "(metric_type = 'duration' AND sport IN ('swimming','gym') "
            "   AND duration_s IS NOT NULL AND distance_m IS NULL AND steps IS NULL) OR "
            "(metric_type = 'count' AND sport = 'steps' "
            "   AND steps IS NOT NULL AND distance_m IS NULL AND duration_s IS NULL)",
            name="ck_activity_metric_matches_sport",
        ),
        # Idempotency: a retried request with the same key never double-counts.
        UniqueConstraint("user_id", "client_request_id", name="uq_activity_client_request"),
        # "Daily" steps: one steps entry per user per day (partial unique index).
        Index("uq_activity_daily_steps", "user_id", "activity_date", unique=True,
              sqlite_where=text("sport = 'steps'")),
        Index("ix_activity_user_date", "user_id", "activity_date"),
        Index("ix_activity_date", "activity_date"),
    )


class LeaderboardEntry(Base):
    """Running totals per user, updated in the same transaction as each activity.

    Reading the leaderboard is then a single indexed scan instead of a SUM over
    all activities. It can always be rebuilt from `activities` (see
    services.rebuild_leaderboard)."""
    __tablename__ = "leaderboard_entries"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="leaderboard")

    __table_args__ = (
        CheckConstraint("total_points >= 0", name="ck_lb_points_non_negative"),
        Index("ix_lb_total_points", "total_points"),
    )

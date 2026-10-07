"""Request/response contracts and validation rules."""
import math
import re
import unicodedata
import uuid
from datetime import date, datetime, timedelta
from typing import Literal, Optional, Union

from pydantic import (BaseModel, ConfigDict, Field, StrictFloat, StrictInt,
                      StrictStr, field_validator, model_validator)
from pydantic_core import PydanticCustomError

from . import config
from .scoring import SPORT_METRIC, ScoringError, km_to_metres, parse_duration

Sport = Literal["running", "walking", "cycling", "swimming", "gym", "steps"]
MetricType = Literal["distance", "duration", "count"]

NAME_RE = re.compile(r"^[^\W\d_]+(?:[ '\-.][^\W\d_]+)*\.?$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalise_name(value: str) -> str:
    """Canonical key for duplicate detection: NFKC, collapsed spaces, casefolded."""
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def _clean_name(value: str) -> str:
    value = " ".join(unicodedata.normalize("NFKC", value).split())
    if not value:
        raise ValueError("must not be blank")
    if not NAME_RE.match(value):
        raise ValueError("may only contain letters, spaces, hyphens, apostrophes and periods")
    return value


# ------------------------------------------------------------------ users

class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    firstName: StrictStr = Field(min_length=1, max_length=50, examples=["Priya"])
    lastName: StrictStr = Field(min_length=1, max_length=50, examples=["Raman"])
    email: Optional[StrictStr] = Field(default=None, max_length=254, examples=["priya@example.com"])

    @field_validator("firstName", "lastName")
    @classmethod
    def _names(cls, v: str) -> str:
        return _clean_name(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        v = v.strip()
        if not EMAIL_RE.match(v):
            raise ValueError("is not a valid email address")
        return v.lower()


class UserOut(BaseModel):
    userId: str
    firstName: str
    lastName: str
    email: Optional[str] = None
    createdAt: datetime
    totalPoints: int = 0
    activityCount: int = 0


# ------------------------------------------------------------- activities

class ActivityCreate(BaseModel):
    """value: number of km (distance), 'min:sec' string (duration), integer (count)."""
    model_config = ConfigDict(extra="forbid")

    userId: StrictStr = Field(examples=["3f1c2a9e-6b1d-4d1e-9d6a-2f0b8c1e4a77"])
    sport: Sport
    metricType: MetricType
    value: Union[StrictInt, StrictFloat, StrictStr]
    activityDate: Optional[date] = None
    notes: Optional[StrictStr] = Field(default=None, max_length=280)
    clientRequestId: Optional[StrictStr] = Field(default=None, min_length=1, max_length=64,
                                                 description="Idempotency key; retries with the same key "
                                                             "return the original activity.")

    # Normalised values, filled in by the validator (not part of the input).
    _distance_m: Optional[int] = None
    _duration_s: Optional[int] = None
    _steps: Optional[int] = None

    @field_validator("userId")
    @classmethod
    def _uuid(cls, v: str) -> str:
        try:
            return str(uuid.UUID(v))
        except ValueError:
            raise ValueError("must be a valid userId (UUID) returned by registration")

    @field_validator("activityDate")
    @classmethod
    def _date(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        today = date.today()
        if v > today:
            raise ValueError("cannot be in the future")
        if v < today - timedelta(days=config.MAX_ACTIVITY_AGE_DAYS):
            raise ValueError(f"cannot be more than {config.MAX_ACTIVITY_AGE_DAYS} days in the past")
        return v

    @model_validator(mode="after")
    def _metric_matches_sport(self):
        expected = SPORT_METRIC[self.sport]
        if self.metricType != expected:
            raise PydanticCustomError(
                "sport_metric_mismatch",
                "sport '{sport}' must be recorded as metricType '{expected}', not '{got}'",
                {"sport": self.sport, "expected": expected, "got": self.metricType},
            )
        v = self.value
        try:
            if expected == "distance":
                if isinstance(v, str) or not math.isfinite(v):
                    raise ValueError("distance value must be a number of kilometres, e.g. 5.25")
                metres = km_to_metres(v)
                if metres <= 0:
                    raise ValueError("distance must be greater than 0")
                if metres > config.MAX_DISTANCE_KM * 1000:
                    raise ValueError(f"distance cannot exceed {config.MAX_DISTANCE_KM} km")
                self._distance_m = metres
            elif expected == "duration":
                if not isinstance(v, str):
                    raise ValueError("duration value must be a 'min:sec' string, e.g. '45:30'")
                secs = parse_duration(v)
                if secs <= 0:
                    raise ValueError("duration must be greater than 0:00")
                if secs > config.MAX_DURATION_SECONDS:
                    raise ValueError("duration cannot exceed 24 hours (1440:00)")
                self._duration_s = secs
            else:  # count
                if not isinstance(v, int):
                    raise ValueError("steps value must be a whole number, e.g. 8500")
                if v <= 0:
                    raise ValueError("steps must be greater than 0")
                if v > config.MAX_DAILY_STEPS:
                    raise ValueError(f"steps cannot exceed {config.MAX_DAILY_STEPS:,} per day")
                self._steps = v
        except ScoringError as exc:
            raise ValueError(str(exc)) from exc
        return self

    @property
    def normalized(self) -> dict:
        return {"distance_m": self._distance_m, "duration_s": self._duration_s, "steps": self._steps}


class ActivityOut(BaseModel):
    activityId: int
    userId: str
    sport: str
    metricType: str
    value: Union[float, int, str]
    normalized: dict
    points: int
    activityDate: date
    notes: Optional[str] = None
    createdAt: datetime

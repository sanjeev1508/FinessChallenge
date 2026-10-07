from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import services
from ..database import IS_MEMORY, get_db
from ..scoring import scoring_rules
from ..schemas import ActivityCreate, ActivityOut, UserCreate, UserOut

router = APIRouter(prefix="/api")

ERRORS = {400: {"description": "Invalid body / sport-metric mismatch"},
          404: {"description": "User not found"}, 409: {"description": "Conflict"}}


@router.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "sqlite-in-memory" if IS_MEMORY else "sqlite-file"}


@router.get("/scoring-rules", tags=["system"])
def get_scoring_rules():
    return {"rules": scoring_rules()}


# ---------------------------------------------------------------- users

@router.post("/users", status_code=201, response_model=UserOut, tags=["users"], responses=ERRORS)
def register_user(body: UserCreate, response: Response, db: Session = Depends(get_db)):
    user = services.register_user(db, body)
    response.headers["Location"] = f"/api/users/{user.id}"
    return services.user_to_dict(user)


@router.get("/users", response_model=list[UserOut], tags=["users"])
def list_users(db: Session = Depends(get_db)):
    return [services.user_to_dict(u) for u in services.list_users(db)]


@router.get("/users/{user_id}", response_model=UserOut, tags=["users"], responses=ERRORS)
def get_user(user_id: str, db: Session = Depends(get_db)):
    return services.user_to_dict(services.get_user(db, user_id))


@router.get("/users/{user_id}/dashboard", tags=["dashboard"], responses=ERRORS)
def get_dashboard(user_id: str, days: int = Query(30, ge=7, le=180), db: Session = Depends(get_db)):
    return services.dashboard(db, user_id, days)


# ----------------------------------------------------------- activities

@router.post("/activities", status_code=201, response_model=ActivityOut, tags=["activities"], responses=ERRORS)
def ingest_activity(body: ActivityCreate, response: Response, db: Session = Depends(get_db)):
    activity, replayed = services.create_activity(db, body)
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
    response.headers["Location"] = f"/api/activities/{activity.id}"
    return services.activity_to_dict(activity)


@router.get("/activities", response_model=list[ActivityOut], tags=["activities"])
def list_activities(userId: Optional[str] = None, limit: int = Query(50, ge=1, le=500),
                    db: Session = Depends(get_db)):
    if userId:
        services.get_user(db, userId)
    return [services.activity_to_dict(a) for a in services.list_activities(db, userId, limit)]


# ---------------------------------------------------------- leaderboard

@router.get("/leaderboard", tags=["leaderboard"])
def get_leaderboard(trendDays: int = Query(7, ge=1, le=90), limit: Optional[int] = Query(None, ge=1, le=1000),
                    db: Session = Depends(get_db)):
    return services.leaderboard(db, trendDays, limit)

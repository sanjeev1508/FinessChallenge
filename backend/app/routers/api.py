from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import services
from ..auth import AuthContext, create_access_token, get_auth_context
from ..database import IS_MEMORY, get_db
from ..scoring import scoring_rules
from ..schemas import (ActivityCreate, ActivityOut, AuthLogin, AuthRegister, AuthTokenOut,
                       PublicUserOut, UserOut)

router = APIRouter(prefix="/api")

ERRORS = {400: {"description": "Invalid body / sport-metric mismatch"},
          401: {"description": "Authentication required"}, 403: {"description": "Forbidden"},
          404: {"description": "User not found"}, 409: {"description": "Conflict"}}


@router.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "sqlite-in-memory" if IS_MEMORY else "sqlite-file"}


@router.get("/scoring-rules", tags=["system"])
def get_scoring_rules():
    return {"rules": scoring_rules()}


# ---------------------------------------------------------------- users

@router.post("/users", status_code=201, response_model=AuthTokenOut, tags=["users"], responses=ERRORS)
def register_user(body: AuthRegister, response: Response, db: Session = Depends(get_db)):
    user = services.register_account(db, body)
    response.headers["Location"] = f"/api/users/{user.id}"
    return {"accessToken": create_access_token(user.id), "user": services.user_to_dict(user)}


@router.post("/auth/login", response_model=AuthTokenOut, tags=["authentication"],
             responses={400: {"description": "Invalid body"}, 401: {"description": "Invalid credentials"}})
def login(body: AuthLogin, db: Session = Depends(get_db)):
    user = services.authenticate_user(db, body)
    return {"accessToken": create_access_token(user.id), "user": services.user_to_dict(user)}


@router.get("/auth/me", response_model=UserOut, tags=["authentication"], responses=ERRORS)
def get_current_account(auth: AuthContext = Depends(get_auth_context)):
    return services.user_to_dict(services.get_user(auth.db, auth.user_id))


@router.get("/users", response_model=list[PublicUserOut], tags=["users"], responses=ERRORS)
def list_users(auth: AuthContext = Depends(get_auth_context)):
    services.get_user(auth.db, auth.user_id)
    return [services.user_to_dict(u) for u in services.list_users(auth.db)]


@router.get("/users/{user_id}", response_model=UserOut, tags=["users"], responses=ERRORS)
def get_user(user_id: str, auth: AuthContext = Depends(get_auth_context)):
    _require_owner(user_id, auth.user_id)
    return services.user_to_dict(services.get_user(auth.db, user_id))


@router.get("/users/{user_id}/dashboard", tags=["dashboard"], responses=ERRORS)
def get_dashboard(user_id: str, days: int = Query(30, ge=7, le=180),
                  auth: AuthContext = Depends(get_auth_context)):
    services.get_user(auth.db, auth.user_id)
    data = services.dashboard(auth.db, user_id, days)
    if user_id != auth.user_id:
        data["user"].pop("email", None)
        for activity in data["recentActivities"]:
            activity.pop("notes", None)
    return data


# ----------------------------------------------------------- activities

@router.post("/activities", status_code=201, response_model=ActivityOut, tags=["activities"], responses=ERRORS)
def ingest_activity(body: ActivityCreate, response: Response, auth: AuthContext = Depends(get_auth_context)):
    _require_owner(body.userId, auth.user_id)
    activity, replayed = services.create_activity(auth.db, body)
    if replayed:
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
    response.headers["Location"] = f"/api/activities/{activity.id}"
    return services.activity_to_dict(activity)


@router.get("/activities", response_model=list[ActivityOut], tags=["activities"], responses=ERRORS)
def list_activities(userId: Optional[str] = None, limit: int = Query(50, ge=1, le=500),
                    auth: AuthContext = Depends(get_auth_context)):
    services.get_user(auth.db, auth.user_id)
    if userId:
        _require_owner(userId, auth.user_id)
    return [services.activity_to_dict(a) for a in services.list_activities(auth.db, auth.user_id, limit)]


# ---------------------------------------------------------- leaderboard

@router.get("/leaderboard", tags=["leaderboard"])
def get_leaderboard(trendDays: int = Query(7, ge=1, le=90), limit: Optional[int] = Query(None, ge=1, le=1000),
                    db: Session = Depends(get_db)):
    return services.leaderboard(db, trendDays, limit)


def _require_owner(requested_user_id: str, authenticated_user_id: str) -> None:
    if requested_user_id != authenticated_user_id:
        raise HTTPException(status_code=403, detail="You can only access your own account data.")

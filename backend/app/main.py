"""Application entry point: API + (optionally) the built React frontend."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .database import SessionLocal, init_db
from .errors import register_error_handlers
from .routers.api import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fitness")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if config.SEED_DEMO:
        with SessionLocal() as db:
            from .seed import seed_demo
            seed_demo(db)
            log.info("Demo data loaded")
    yield


app = FastAPI(title="Fitness Challenge API", version="1.0.0", lifespan=lifespan,
              description="Register users, ingest activities, and compete on a normalised points leaderboard.")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
register_error_handlers(app)
app.include_router(router)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_not_found(path: str):
    # Unknown /api/* routes return JSON 404 instead of falling through to the SPA.
    return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND",
                                                            "message": f"No API route /api/{path}"}})


if STATIC_DIR.exists():
    # The React build. HashRouter is used on the client, so no SPA fallback is needed.
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"message": "API is running. Frontend build not found; see README. API docs at /docs"}

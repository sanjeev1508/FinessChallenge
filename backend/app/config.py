"""Runtime configuration, read once from environment variables."""
import os

# Default is an in-memory SQLite database (fast, zero setup, resets on restart).
# Set DATABASE_URL=sqlite:///./fitness.db to persist data to a file instead.
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///:memory:")

# Load demo users and activities on startup so the leaderboard is not empty.
SEED_DEMO: bool = os.getenv("SEED_DEMO", "true").strip().lower() not in {"0", "false", "no"}

# Origins allowed to call the API during frontend development (Vite dev server).
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

# Validation limits (sanity bounds that reject obviously bogus data).
MAX_DISTANCE_KM = 1000          # per activity
MAX_DURATION_SECONDS = 24 * 3600  # per activity
MAX_DAILY_STEPS = 200_000
MAX_ACTIVITY_AGE_DAYS = 365

# Fitness Challenge

[![Checks](https://github.com/sanjeev1508/FinessChallenge/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjeev1508/FinessChallenge/actions/workflows/ci.yml)

Log runs, walks, rides, swims, gym sessions and daily steps. Every activity converts to points, so everyone competes on one leaderboard, and each person gets a dashboard of their training.

React frontend · FastAPI backend · SQLite (in-memory by default). See [DESIGN.md](DESIGN.md) for the full design document.

## Architecture

```text
React UI <-> FastAPI REST APIs <-> Business services <-> SQLite
                 |                     |
          Request validation    Scoring normalization
```

- **Frontend:** responsive global leaderboard with ranking trends, and participant dashboards with activity history, volume over time and sport breakdowns. Signed-in users can view any athlete's dashboard.
- **Accounts:** register and log in with email and password; passwords are Argon2-hashed and successful authentication returns a short-lived JWT.
- **Activities:** requires the signed-in user, validates sport/metric combinations, calculates integer points, and saves the activity and leaderboard update in one transaction.
- **Scoring:** floors distance points, counts only completed duration minutes, and awards steps in complete blocks of 100.
- **Database:** related `users`, `auth_accounts`, `activities` and `leaderboard_entries` tables; rankings use total points, with historical movement based on submission timestamps.

FastAPI serves the built React app and API from one origin. Schema, API contracts, data flows and trade-offs are detailed in [DESIGN.md](DESIGN.md).

## Run it (the only requirement is Python 3.10+)

The React app is already built and bundled inside `backend/app/static`, so **Node.js is not needed** to run it.

1. Install Python 3.10 or newer from <https://www.python.org/downloads/> (on Windows, tick **"Add python.exe to PATH"** in the installer).
2. Unzip the folder.
3. Start it:
   - **Windows:** double-click `start.bat`
   - **macOS / Linux:** open a terminal in the folder and run `./start.sh`
4. Open <http://localhost:8000>. The first start takes about a minute while dependencies install; later starts are instant.

Stop the server with `Ctrl+C` (or close the window).

The app starts with 8 demo athletes and about a month of activity so the leaderboard and charts have something to show. Click **Join challenge** to create an account with your name, email, and an 8-128 character password. After signing in, use **My dashboard** or **Log activity**; click an athlete's name on the leaderboard to view their read-only dashboard. Seeded athletes have no login until you explicitly provision dummy credentials for a file database.

### Open it from a phone on the same Wi-Fi
Run `start.bat lan` (Windows) or `./start.sh lan` (macOS/Linux), then open `http://<your-computer's-IP>:8000` on the phone. Find the IP with `ipconfig` (Windows) or `ipconfig getifaddr en0` (Mac). Allow Python through the firewall if asked.

### Keep data between restarts
The default database lives in memory and resets each time the server stops. To save to a file instead:

```bash
# macOS / Linux
DATABASE_URL=sqlite:///./fitness.db ./start.sh
# Windows (Command Prompt)
set DATABASE_URL=sqlite:///./fitness.db && start.bat
```

Set `SEED_DEMO=false` to start with an empty board.

In PowerShell, run from the project root:

```powershell
$env:DATABASE_URL = "sqlite:///./fitness.db"
.\start.bat
```

The launcher switches into `backend`, so this relative URL uses `backend/fitness.db`. Let dependency installation complete; no manual virtual-environment activation is needed. If CMD asks `Terminate batch job (Y/N)?`, type `Y` to return to PowerShell before entering another command.

All calendar days use UTC, including activity dates, daily steps, streaks and ranking comparisons.

### Dummy logins for existing local data

For a **local/demo file database only**, create unique dummy emails and randomly generated passwords for participants that have no login yet. Working login accounts, participant IDs, activities and leaderboard totals are preserved. This is opt-in, not an automatic production migration.

Run from `backend`, using the same `DATABASE_URL` as your server (PowerShell example):

```powershell
$env:DATABASE_URL = "sqlite:///./fitness.db"
.\.venv\Scripts\python.exe -m app.provision_dummy_accounts --output local.dummy-credentials.csv
```

Back up the file database before provisioning. The private CSV contains each affected participant's email and password. Passwords are stored in the database only as Argon2 hashes. Keep the CSV private and out of version control (`*.dummy-credentials.csv` is ignored); delete it when no longer needed. Re-running with a new output path preserves working accounts and never resets passwords. An existing CSV is never overwritten. An in-memory database cannot be updated from a separate process.

If the join page still says email is optional or has no password field, hard-refresh with **Ctrl+Shift+R**, or open <http://localhost:8000/?refresh=auth#/login> in a private browser window. The HTML shell uses `Cache-Control: no-cache` and the built assets have content-hashed filenames. When changing UI source, rebuild with `npm run build` from `frontend`; restart the server after backend changes.

## Manual setup (developers)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # http://localhost:8000, API docs at /docs
pytest -q                            # API, scoring and concurrency regressions

# Frontend (Node.js 20.19+ or 22.12+, only for UI development)
# In a second terminal:
cd frontend
npm ci
npm run dev                          # http://localhost:5173, proxies /api to :8000
npm run build                        # rebuilds into backend/app/static
npm test                             # Node's built-in test runner; no extra framework
npm audit                            # dependency advisories
```

## Automated checks

GitHub Actions runs backend tests on Windows and Linux with Python 3.10 and 3.14, using both in-memory and file SQLite. Regressions cover authentication, owner-only writes, shared-dashboard privacy, and dummy credential provisioning (history preservation, collision handling, reruns, export failures and rollback). Frontend checks cover scoring previews, API errors, cancellation, UTC dates and bundle budgets, plus a production build and dependency audit. CI also verifies that the committed frontend bundle matches its source.

The initial JavaScript bundle must stay below 250 kB and every JavaScript chunk below 500 kB. Build before running frontend tests if you changed UI source.

## API quick reference

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/users` | Register with name, email, and password; returns user data and a JWT |
| POST | `/api/auth/login` | Log in and receive a JWT |
| GET | `/api/auth/me` | Return the signed-in user's account |
| POST | `/api/activities` | Log an activity; requires a JWT |
| GET | `/api/leaderboard?trendDays=7` | Ranked standings with movement |
| GET | `/api/users/{id}/dashboard?days=30` | Participant stats; requires a JWT; other participants' email and activity notes stay private |
| GET | `/api/users`, `/api/users/{id}`, `/api/activities` | Account/activity reads; require a JWT |
| GET | `/api/scoring-rules`, `/api/health` | Public system information |

Dashboard windows accept 7-180 days (default 30). Shared dashboards include statistics, charts, sport totals and recent activity metrics, but omit the other athlete's email and activity notes. `/api/users/{id}` and `/api/activities` remain owner-only; the user list omits all emails.

Full request/response specs: <http://localhost:8000/docs> while the server runs, or DESIGN.md section c.

### Authentication

Signed-in participants can click any athlete's name on the leaderboard to view a read-only dashboard. Only your own dashboard offers activity logging; the API rejects writes for anyone else. Email addresses and activity notes are visible only to the owner.

Send the returned token on protected requests as `Authorization: Bearer <accessToken>`. Tokens expire after 60 minutes. The leaderboard, health check, and scoring rules stay public. Signed-in users can view participant dashboards; private account reads and activity writes remain owner-only. Older accounts without credentials need the opt-in local dummy-login backfill before they can log in. A new account must use a name not already registered.

If `JWT_SECRET_KEY` is not set, the app generates a temporary key at startup, so users must log in again after a server restart. Set a private, stable `JWT_SECRET_KEY` in the environment for deployments; never commit it to source control.

```bash
curl -X POST localhost:8000/api/users -H "Content-Type: application/json" \
     -d '{"firstName":"Asha","lastName":"Kumar","email":"asha@example.com","password":"choose-a-strong-password"}'
# The response includes accessToken and user.userId.

curl -X POST localhost:8000/api/activities -H "Content-Type: application/json" \
     -H "Authorization: Bearer <accessToken>" \
     -d '{"userId":"<user.userId from above>","sport":"walking","metricType":"distance","value":1.55}'
# -> "points": 77
```

| Sport | metricType | value format | Points |
|---|---|---|---|
| running / walking / cycling | `distance` | number of km, e.g. `5.25` | 100 / 50 / 25 per km, floored |
| swimming / gym | `duration` | `"min:sec"`, e.g. `"45:30"` | 15 / 5 per full minute |
| steps | `count` | integer, e.g. `8500` | 1 per full 100 steps |

## Project layout

```
fitness-challenge/
├── start.bat / start.sh      one-command launch
├── DESIGN.md                 design document
├── backend/
│   ├── app/
│   │   ├── main.py           app, static frontend, startup
│   │   ├── config.py         env-driven settings and limits
│   │   ├── database.py       engine, sessions, SQLite tuning
│   │   ├── models.py         users, auth_accounts, activities, leaderboard_entries
│   │   ├── schemas.py        request validation
│   │   ├── auth.py           Argon2 password checks and JWT tokens
│   │   ├── scoring.py        normalisation and points (integer maths)
│   │   ├── services.py       business logic and transactions
│   │   ├── errors.py         uniform error responses
│   │   ├── seed.py           demo data
│   │   ├── provision_dummy_accounts.py  opt-in local legacy login backfill
│   │   ├── routers/api.py    HTTP endpoints
│   │   └── static/           built React app
│   └── tests/                pytest suite
└── frontend/                 React source (Vite)
```

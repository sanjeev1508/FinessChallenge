# Fitness Challenge

Log runs, walks, rides, swims, gym sessions and daily steps. Every activity converts to points, so everyone competes on one leaderboard, and each person gets a dashboard of their training.

React frontend · FastAPI backend · SQLite (in-memory by default). See [DESIGN.md](DESIGN.md) for the full design document.

## Run it (the only requirement is Python 3.10+)

The React app is already built and bundled inside `backend/app/static`, so **Node.js is not needed** to run it.

1. Install Python 3.10 or newer from <https://www.python.org/downloads/> (on Windows, tick **"Add python.exe to PATH"** in the installer).
2. Unzip the folder.
3. Start it:
   - **Windows:** double-click `start.bat`
   - **macOS / Linux:** open a terminal in the folder and run `./start.sh`
4. Open <http://localhost:8000>. The first start takes about a minute while dependencies install; later starts are instant.

Stop the server with `Ctrl+C` (or close the window).

The app starts with 8 demo athletes and about a month of activity so the leaderboard and charts have something to show. Click **Log activity**, or **My dashboard → Join the challenge** to add yourself.

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

All calendar days use UTC, including activity dates, daily steps, streaks and ranking comparisons.

## Manual setup (developers)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # http://localhost:8000, API docs at /docs
pytest -q                            # 39 tests

# Frontend (Node.js 20.19+ or 22.12+, only for UI development)
# In a second terminal:
cd frontend
npm ci
npm run dev                          # http://localhost:5173, proxies /api to :8000
npm run build                        # rebuilds into backend/app/static
```

## API quick reference

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/users` | Register; returns `userId`. 409 on duplicate first+last name |
| POST | `/api/activities` | Log an activity; 400 on invalid body or sport/metric mismatch |
| GET | `/api/leaderboard?trendDays=7` | Ranked standings with movement |
| GET | `/api/users/{id}/dashboard?days=30` | Personal stats and chart data |
| GET | `/api/users`, `/api/activities`, `/api/scoring-rules`, `/api/health` | Supporting reads |

Full request/response specs: <http://localhost:8000/docs> while the server runs, or DESIGN.md section c.

```bash
curl -X POST localhost:8000/api/users -H "Content-Type: application/json" \
     -d '{"firstName":"Asha","lastName":"Kumar"}'

curl -X POST localhost:8000/api/activities -H "Content-Type: application/json" \
     -d '{"userId":"<id from above>","sport":"walking","metricType":"distance","value":1.55}'
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
│   │   ├── models.py         users, activities, leaderboard_entries
│   │   ├── schemas.py        request validation
│   │   ├── scoring.py        normalisation and points (integer maths)
│   │   ├── services.py       business logic and transactions
│   │   ├── errors.py         uniform error responses
│   │   ├── seed.py           demo data
│   │   ├── routers/api.py    HTTP endpoints
│   │   └── static/           built React app
│   └── tests/                pytest suite
└── frontend/                 React source (Vite)
```

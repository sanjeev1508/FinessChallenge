#!/usr/bin/env bash
# Fitness Challenge: one-command start for macOS / Linux.
#   ./start.sh        -> only this computer   (http://localhost:8000)
#   ./start.sh lan    -> also phones/laptops on the same Wi-Fi
set -e
cd "$(dirname "$0")/backend"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
if ! $PY -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
  echo "Python 3.10 or newer is required. Install it from https://www.python.org/downloads/"
  exit 1
fi

if [ ! -d .venv ]; then
  echo "First run: creating a virtual environment..."
  $PY -m venv .venv
fi
. .venv/bin/activate
echo "Installing dependencies (first run takes a minute)..."
python -m pip install -q --disable-pip-version-check -r requirements.txt

HOST=127.0.0.1
if [ "$1" = "lan" ]; then
  HOST=0.0.0.0
  IP=$( (ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}') )
  echo "Other devices on your Wi-Fi can open: http://${IP:-<your-ip>}:8000"
fi
echo ""
echo "  Fitness Challenge is starting at http://localhost:8000"
echo "  API docs: http://localhost:8000/docs     Stop: Ctrl+C"
echo ""
python -m uvicorn app.main:app --host "$HOST" --port 8000

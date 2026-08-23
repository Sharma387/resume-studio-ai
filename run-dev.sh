#!/usr/bin/env bash
# Run both RSAI dev servers (backend + frontend) with one command.
# Kills anything already on :8000 / :5173 first, then starts:
#   Backend: uv run uvicorn on :8000 | Frontend: npm run dev on :5173
# Ctrl-C stops both and cleans up.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_LOG="$ROOT/.dev-backend.log"
FRONTEND_LOG="$ROOT/.dev-frontend.log"

BACK_PID=""
FRONT_PID=""

# Kill any process listening on the given TCP port (macOS/Linux).
free_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Freeing port $port (pids: $pids) ..."
    kill $pids 2>/dev/null || true
    sleep 1
    # Force-kill anything still holding it.
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
  fi
}

# Kill stray dev processes by name (covers crashed/orphaned servers).
kill_strays() {
  pkill -f "uvicorn app.main:app" 2>/dev/null || true
  pkill -f "vite" 2>/dev/null || true
}

cleanup() {
  echo ""
  echo "Stopping servers..."
  [ -n "$BACK_PID" ] && kill "$BACK_PID" 2>/dev/null || true
  [ -n "$FRONT_PID" ] && kill "$FRONT_PID" 2>/dev/null || true
  kill_strays
  wait 2>/dev/null || true
  echo "Done."
}
trap cleanup INT TERM EXIT

echo "Cleaning up any existing servers on :8000 / :5173 ..."
free_port 8000
free_port 5173
kill_strays
sleep 1

echo "Starting backend (uv run uvicorn :8000) ..."
( cd "$ROOT/backend" && exec uv run uvicorn app.main:app --reload --port 8000 ) \
  > "$BACKEND_LOG" 2>&1 &
BACK_PID=$!

echo "Starting frontend (npm run dev :5173) ..."
( cd "$ROOT/frontend" && exec npm run dev ) \
  > "$FRONTEND_LOG" 2>&1 &
FRONT_PID=$!

echo ""
echo "Backend  -> http://localhost:8000   (log: $BACKEND_LOG)"
echo "Frontend -> http://localhost:5173   (log: $FRONTEND_LOG)"
echo "Press Ctrl-C to stop both."
echo ""

tail -F "$BACKEND_LOG" "$FRONTEND_LOG" &
TAIL_PID=$!
wait "$TAIL_PID"

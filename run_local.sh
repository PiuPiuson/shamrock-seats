#!/usr/bin/env bash

# Exit on any error
set -e

# ---------------------------------------------
# Local-development launcher for Shamrock Seats
# ---------------------------------------------
# 1) Exports variables from a .env file if it exists.
# 2) Forces HEADLESS=0 so you can see the Selenium browser.
# 3) Tries to autodetect CHROMEDRIVER_PATH if not set.
# 4) Delegates execution to the bot.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Load environment from .env (if present)
if [[ -f .env ]]; then
  echo "Loading variables from .env"
  set -a  # export everything loaded by `source`
  source .env
  set +a
fi

# Override headless mode for local dev
export HEADLESS=0

# If CHROMEDRIVER_PATH is not set, attempt to discover it
if [[ -z "$CHROMEDRIVER_PATH" ]]; then
  if command -v chromedriver >/dev/null 2>&1; then
    export CHROMEDRIVER_PATH="$(command -v chromedriver)"
    echo "Discovered chromedriver at $CHROMEDRIVER_PATH"
  else
    # Fallback to default path inside Docker image
    export CHROMEDRIVER_PATH="/usr/bin/chromedriver"
    echo "chromedriver not found in PATH — defaulting to $CHROMEDRIVER_PATH"
  fi
fi

cd "bot"
# Run the bot (forwarding any additional arguments)
python bot.py "$@" 
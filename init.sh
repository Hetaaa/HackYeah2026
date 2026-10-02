#!/usr/bin/env bash
# Sets up the backend environment: uv, Python 3.12, dependencies, .env, then runs lint + tests.
# Usage: ./init.sh [--skip-checks]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_CHECKS=0

for arg in "$@"; do
    case "$arg" in
        --skip-checks) SKIP_CHECKS=1 ;;
        -h | --help)
            echo "Usage: ./init.sh [--skip-checks]"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

step() {
    printf '\033[36m==> %s\033[0m\n' "$*"
}

step "Checking uv"
if ! command -v uv >/dev/null 2>&1; then
    step "uv not found, installing with the official installer"
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    else
        wget -qO- https://astral.sh/uv/install.sh | sh
    fi
    # The installer updates PATH for new shells only; add it to this one as well.
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        echo "uv was installed but is not on PATH. Open a new shell and run ./init.sh again." >&2
        exit 1
    fi
fi
uv --version

cd "$ROOT/backend"

step "Installing Python 3.12 and dependencies (uv sync)"
uv sync

if [[ ! -f .env && -f .env.example ]]; then
    step "Creating backend/.env from .env.example"
    cp .env.example .env
fi

if [[ "$SKIP_CHECKS" -eq 0 ]]; then
    step "Running lint and tests"
    uv run ruff check .
    uv run pytest -q
fi

step "Optional tools"
for tool in docker node; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "    $tool found"
    else
        printf '\033[33m    %s not found (optional: docker for image builds, node for the frontend)\033[0m\n' "$tool"
    fi
done

printf '\n\033[32mDone. Start the API:\033[0m\n'
echo "    cd backend && uv run uvicorn app.main:app --reload"
echo "    http://localhost:8000/docs"

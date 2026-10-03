#!/usr/bin/env bash
# Full PMData pipeline: raw pmdata/ -> analysis/output/ (+ validation + tests).
#
#   ./run_pipeline.sh                  use cached heavy inputs (wear minutes, HR-derived), ~1 min
#   ./run_pipeline.sh --rebuild-cache  rescan heart_rate.json for all participants first (slow)
#   ./run_pipeline.sh --skip-validation
#
# Steps:
#   1. clean.py     cleaned daily table, participants, feature config      -> output/daily_*.csv, *.json
#   2. reasons.py   patterns (engine.py) + calendar reasons + comparisons  -> output/patterns.json, calendar.json
#   3. validate.py  null labels, setting variants, split-half, weekdays,
#                   injected effect                                        -> output/validation.json/.md
#   4. pytest       test_clean.py + test_engine.py
set -euo pipefail
cd "$(dirname "$0")"

UV=(uv run -q --with pandas --with numpy --with pyarrow)
REBUILD=""
VALIDATE=1
for arg in "$@"; do
  case "$arg" in
    --rebuild-cache) REBUILD="--rebuild-cache" ;;
    --skip-validation) VALIDATE=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

echo "== 1/4 clean"
# --rebuild-cache rescans heart_rate.json (wear minutes) and clears cache/hr_derived/, which clean.py refills
"${UV[@]}" python -W ignore clean.py $REBUILD

echo "== 2/4 patterns + calendar"
"${UV[@]}" python -W ignore reasons.py | grep -v "reasons:"

if [[ "$VALIDATE" == 1 ]]; then
  echo "== 3/4 validation (~1 min)"
  "${UV[@]}" python -W ignore validate.py --runs 100 | grep -v "^setting"
else
  echo "== 3/4 validation skipped"
fi

echo "== 4/4 tests"
"${UV[@]}" --with pytest python -m pytest test_clean.py test_engine.py -q -p no:warnings
echo "done -> $(pwd)/output"

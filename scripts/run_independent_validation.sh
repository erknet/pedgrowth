#!/usr/bin/env bash
# Run independent WHO/CDC R validation inside the project or in GitHub Actions.
# Requires CRAN anthroplus + cdcanthro and the normal pygrowup Python package.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -x ".local/r/bin/Rscript" ]]; then
  R_BIN="$PWD/.local/r/bin/Rscript"
  export R_LIBS_USER="$PWD/.local/r-library"
else
  R_BIN="${R_BIN:-Rscript}"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
mkdir -p .local/validation
"$R_BIN" --vanilla scripts/export_official.R .local/validation/official-values.csv
"$PYTHON_BIN" scripts/validate_official.py .local/validation/official-values.csv
printf 'Independent test data: %s\n' "$PWD/.local/validation/official-values.csv"

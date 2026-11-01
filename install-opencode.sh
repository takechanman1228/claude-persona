#!/usr/bin/env bash
# Offline installer for the OpenCode port of claude-persona.
# Run from a checkout/copy of this repo:  ./install-opencode.sh [--wheels DIR]
#   --wheels DIR  install pandas/matplotlib/seaborn from a local wheelhouse
#                 (pip --no-index); otherwise pip is never invoked.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
OC_DIR="${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}"
SKILL_DIR="${OC_DIR}/skills/persona"
WHEELS=""

while [ $# -gt 0 ]; do
    case "$1" in
        --wheels) WHEELS="${2:?--wheels needs a directory}"; shift 2 ;;
        -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required." >&2; exit 1; }
python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null || {
    echo "Error: Python 3.10+ is required. Found: $(python3 --version)" >&2; exit 1; }
command -v opencode >/dev/null 2>&1 || echo "[warn] opencode not found on PATH (needed at runtime)."

echo "[..] Installing skill into ${SKILL_DIR}"
rm -rf "${SKILL_DIR}"
mkdir -p "${SKILL_DIR}" "${OC_DIR}/commands"
for d in scripts references templates demo; do cp -R "${SRC}/${d}" "${SKILL_DIR}/${d}"; done
cp "${SRC}/requirements.txt" "${SRC}/README.md" "${SRC}/LICENSE" "${SKILL_DIR}/"
python3 "${SRC}/opencode/port_skill.py" "${SRC}/skills/persona/SKILL.md" "${SKILL_DIR}" > "${SKILL_DIR}/SKILL.md"
sed "s|{{SKILL_DIR}}|${SKILL_DIR}|g" "${SRC}/opencode/persona-command.md" > "${OC_DIR}/commands/persona.md"
echo "[ok] Skill + /persona command installed"

if python3 -c "import pandas, matplotlib, seaborn" 2>/dev/null; then
    echo "[ok] Analysis dependencies already available"
elif [ -n "${WHEELS}" ]; then
    python3 -m pip install --user --no-index --find-links "${WHEELS}" -r "${SKILL_DIR}/requirements.txt"
    echo "[ok] Analysis dependencies installed from ${WHEELS}"
else
    echo "[warn] pandas/matplotlib/seaborn missing: simulation works, analysis/charts need them."
    echo "       On a machine with internet:  pip download -r requirements.txt -d wheels"
    echo "       Then here:                   ./install-opencode.sh --wheels wheels"
fi

echo ""
echo "Done. Restart OpenCode, then try:  /persona generate 5 running shoe shoppers in the US"

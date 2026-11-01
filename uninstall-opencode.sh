#!/usr/bin/env bash
set -euo pipefail
OC_DIR="${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}"
rm -rf "${OC_DIR}/skills/persona" "${OC_DIR}/commands/persona.md"
echo "[ok] claude-persona removed from ${OC_DIR}. Restart OpenCode."

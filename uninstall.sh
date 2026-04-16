#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="${HOME}/.claude/skills/persona"

echo "This will remove claude-persona from ${SKILL_DIR}"
read -rp "Continue? [y/N] " confirm

if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

rm -rf "${SKILL_DIR}"
echo "[ok] claude-persona removed. Restart Claude Code to complete removal."

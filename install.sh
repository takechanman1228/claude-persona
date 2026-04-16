#!/usr/bin/env bash
set -euo pipefail

main() {
    VERSION="0.1.0"
    SKILL_DIR="${HOME}/.claude/skills/persona"
    REPO_URL="https://github.com/takechanman1228/claude-persona"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

    echo "=============================================="
    echo "  claude-persona installer"
    echo "  Decision-focused persona research for Claude Code"
    echo "=============================================="
    echo ""

    command -v git >/dev/null 2>&1 || {
        echo "Error: git is required but not installed."
        exit 1
    }

    command -v python3 >/dev/null 2>&1 || {
        echo "Error: python3 is required but not installed."
        exit 1
    }

    python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null || {
        echo "Error: Python 3.10+ is required. Found: $(python3 --version)"
        exit 1
    }

    if [ "$(basename "$0")" = "install.sh" ] && [ -f "${SCRIPT_DIR}/skills/persona/SKILL.md" ]; then
        SRC="${SCRIPT_DIR}"
        echo "[ok] Installing from local source"
    else
        TEMP_DIR="$(mktemp -d)"
        trap 'rm -rf "${TEMP_DIR}"' EXIT
        echo "[..] Downloading ${REPO_URL}"
        git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/claude-persona" >/dev/null 2>&1
        SRC="${TEMP_DIR}/claude-persona"
        echo "[ok] Downloaded repository"
    fi

    echo "[..] Installing files into ${SKILL_DIR}"
    rm -rf "${SKILL_DIR}"
    mkdir -p "${SKILL_DIR}"

    cp "${SRC}/skills/persona/SKILL.md" "${SKILL_DIR}/SKILL.md"
    cp "${SRC}/CLAUDE.md" "${SKILL_DIR}/CLAUDE.md"
    cp "${SRC}/README.md" "${SKILL_DIR}/README.md"
    cp "${SRC}/CHANGELOG.md" "${SKILL_DIR}/CHANGELOG.md"
    cp "${SRC}/requirements.txt" "${SKILL_DIR}/requirements.txt"
    cp -R "${SRC}/scripts" "${SKILL_DIR}/scripts"
    cp -R "${SRC}/references" "${SKILL_DIR}/references"
    cp -R "${SRC}/templates" "${SKILL_DIR}/templates"
    cp -R "${SRC}/demo" "${SKILL_DIR}/demo"
    cp -R "${SRC}/docs" "${SKILL_DIR}/docs"
    cp -R "${SRC}/assets" "${SKILL_DIR}/assets"

    echo "[..] Installing Python dependencies (best effort)"
    if python3 -m pip install --user -r "${SKILL_DIR}/requirements.txt" >/dev/null 2>&1; then
        echo "[ok] Python dependencies installed"
    else
        echo "[warn] Could not install Python dependencies automatically."
        echo "       Run manually:"
        echo "       python3 -m pip install --user -r ${SKILL_DIR}/requirements.txt"
    fi

    echo ""
    echo "[ok] claude-persona ${VERSION} installed"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code"
    echo "  2. Run /persona concept-test Running shoes: 3 concepts"
    echo ""
    echo "Plugin users can also add the marketplace entry with:"
    echo "  /plugin marketplace add takechanman1228/claude-persona"
    echo "  /plugin install claude-persona@claude-persona"
}

main "$@"

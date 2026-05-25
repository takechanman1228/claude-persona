"""Asset link smoke tests for claude-persona.

Run from repository root:
    python3 -m unittest tests/test_markdown_asset_links.py
"""

from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|\[[^\]]+\]\(([^)]+)\)")


def _is_external(target: str) -> bool:
    target = target.strip()
    return (
        target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
        or target.startswith("#")
    )


def _strip_anchor(target: str) -> str:
    return target.split("#", 1)[0].strip()


def _markdown_files() -> list[Path]:
    ignored_parts = {".git", ".venv", "node_modules", "__pycache__"}
    files = []
    for path in REPO_ROOT.rglob("*.md"):
        if ignored_parts & set(path.parts):
            continue
        files.append(path)
    return sorted(files)


class MarkdownAssetLinkTests(unittest.TestCase):
    def test_local_asset_links_exist(self):
        missing = []
        for md_path in _markdown_files():
            text = md_path.read_text(encoding="utf-8")
            for match in MARKDOWN_LINK_RE.finditer(text):
                target = match.group(1) or match.group(2) or ""
                target = _strip_anchor(target)
                if not target or _is_external(target):
                    continue
                if "assets/" not in target and not target.startswith("../assets/"):
                    continue

                resolved = (md_path.parent / target).resolve()
                try:
                    resolved.relative_to(REPO_ROOT.resolve())
                except ValueError:
                    missing.append(f"{md_path.relative_to(REPO_ROOT)} -> {target} escapes repo")
                    continue
                if not resolved.exists():
                    missing.append(f"{md_path.relative_to(REPO_ROOT)} -> {target}")

        self.assertEqual(missing, [], "Missing local asset links:\n" + "\n".join(missing))

    def test_svg_assets_parse_as_xml(self):
        failures = []
        for svg_path in sorted((REPO_ROOT / "assets").glob("*.svg")):
            try:
                ET.parse(svg_path)
            except ET.ParseError as exc:
                failures.append(f"{svg_path.relative_to(REPO_ROOT)}: {exc}")
        self.assertEqual(failures, [], "Invalid SVG assets:\n" + "\n".join(failures))

    def test_png_assets_have_png_signature(self):
        failures = []
        signature = b"\x89PNG\r\n\x1a\n"
        for png_path in sorted((REPO_ROOT / "assets").glob("*.png")):
            if png_path.read_bytes()[:8] != signature:
                failures.append(str(png_path.relative_to(REPO_ROOT)))
        self.assertEqual(failures, [], "Invalid PNG signatures:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()

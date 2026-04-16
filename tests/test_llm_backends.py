import importlib.util
import unittest
from pathlib import Path
from unittest import mock


def load_module(module_name: str, relative_path: str):
    script_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


llm_backends = load_module("llm_backends", "scripts/llm_backends.py")


class ResolveBackendTests(unittest.TestCase):
    def test_auto_prefers_codex_when_codex_runtime_marker_is_present(self):
        env = {"CODEX_THREAD_ID": "abc123"}
        with mock.patch.object(llm_backends, "backend_available", side_effect=lambda backend: backend == "codex-cli"):
            self.assertEqual(llm_backends.resolve_backend("auto", env=env), "codex-cli")

    def test_claude_gets_default_model_but_codex_does_not(self):
        self.assertEqual(llm_backends.resolve_model(None, "claude-cli"), "sonnet")
        self.assertIsNone(llm_backends.resolve_model(None, "codex-cli"))

    def test_report_backend_same_uses_simulation_backend(self):
        self.assertEqual(
            llm_backends.resolve_report_backend("same", "codex-cli"),
            "codex-cli",
        )

    def test_preview_command_shows_codex_structured_output_flags(self):
        preview = llm_backends.preview_command(
            "codex-cli",
            model="gpt-5",
            structured_output=True,
        )
        self.assertIn("codex -a never -s read-only", preview)
        self.assertIn("--output-schema /tmp/schema.json", preview)
        self.assertIn("-m gpt-5", preview)


if __name__ == "__main__":
    unittest.main()

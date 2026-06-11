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


ALL_CAPS = {flag: True for flag in llm_backends.CLAUDE_CAPABILITY_FLAGS}
NO_CAPS = {flag: False for flag in llm_backends.CLAUDE_CAPABILITY_FLAGS}

NEW_CLI_HELP = """
Options:
  --json-schema <schema>     JSON Schema for structured output validation
  --safe-mode                Start with all customizations disabled
  --fallback-model <model>   Enable automatic fallback to specified model(s)
  --effort <level>           Effort level for the current session
  --max-budget-usd <amount>  Maximum dollar amount to spend on API calls
  --model <model>            Model for the current session
"""

OLD_CLI_HELP = """
Options:
  --output-format <format>   Output format
  --model <model>            Model for the current session
  --tools <tools...>         Specify the list of available tools
"""


class CapabilityDetectionTests(unittest.TestCase):
    def test_detects_all_flags_in_new_cli_help(self):
        caps = llm_backends.detect_claude_capabilities(help_text=NEW_CLI_HELP)
        self.assertEqual(caps, ALL_CAPS)

    def test_detects_no_optional_flags_in_old_cli_help(self):
        caps = llm_backends.detect_claude_capabilities(help_text=OLD_CLI_HELP)
        self.assertEqual(caps, NO_CAPS)


class ClaudeCommandBuilderTests(unittest.TestCase):
    def test_legacy_flags_are_always_present(self):
        cmd = llm_backends._build_claude_print_command(
            "sys", model="sonnet", capabilities=NO_CAPS,
        )
        self.assertEqual(
            cmd,
            [
                "claude", "-p",
                "--system-prompt", "sys",
                "--output-format", "json",
                "--tools", "",
                "--no-session-persistence",
                "--model", "sonnet",
            ],
        )

    def test_json_schema_flag_requires_schema_and_capability(self):
        schema = {"type": "object"}
        with_schema = llm_backends._build_claude_print_command(
            "sys", json_schema=schema, isolation=False, capabilities=ALL_CAPS,
        )
        self.assertIn("--json-schema", with_schema)
        self.assertIn('{"type": "object"}', with_schema)

        without_capability = llm_backends._build_claude_print_command(
            "sys", json_schema=schema, isolation=False, capabilities=NO_CAPS,
        )
        self.assertNotIn("--json-schema", without_capability)

        without_schema = llm_backends._build_claude_print_command(
            "sys", isolation=False, capabilities=ALL_CAPS,
        )
        self.assertNotIn("--json-schema", without_schema)

    def test_safe_mode_defaults_on_and_can_be_disabled(self):
        default_cmd = llm_backends._build_claude_print_command(
            "sys", capabilities=ALL_CAPS,
        )
        self.assertIn("--safe-mode", default_cmd)

        opted_out = llm_backends._build_claude_print_command(
            "sys", isolation=False, capabilities=ALL_CAPS,
        )
        self.assertNotIn("--safe-mode", opted_out)

        old_cli = llm_backends._build_claude_print_command(
            "sys", capabilities=NO_CAPS,
        )
        self.assertNotIn("--safe-mode", old_cli)

    def test_reliability_flags_are_emitted_when_set_and_supported(self):
        cmd = llm_backends._build_claude_print_command(
            "sys",
            model="fable",
            fallback_model="sonnet",
            effort="medium",
            max_budget_usd=0.5,
            capabilities=ALL_CAPS,
        )
        self.assertIn("--fallback-model", cmd)
        self.assertIn("sonnet", cmd)
        self.assertIn("--effort", cmd)
        self.assertIn("medium", cmd)
        self.assertIn("--max-budget-usd", cmd)
        self.assertIn("0.5", cmd)
        # Model stays the trailing pair.
        self.assertEqual(cmd[-2:], ["--model", "fable"])

        old_cli = llm_backends._build_claude_print_command(
            "sys",
            fallback_model="sonnet",
            effort="medium",
            max_budget_usd=0.5,
            capabilities=NO_CAPS,
        )
        self.assertNotIn("--fallback-model", old_cli)
        self.assertNotIn("--effort", old_cli)
        self.assertNotIn("--max-budget-usd", old_cli)

    def test_preview_command_shows_claude_isolation_and_schema(self):
        preview = llm_backends.preview_command(
            "claude-cli",
            model="sonnet",
            structured_output=True,
            capabilities=ALL_CAPS,
        )
        self.assertIn("--safe-mode", preview)
        self.assertIn("--json-schema", preview)
        self.assertIn("--model sonnet", preview)

        no_isolation = llm_backends.preview_command(
            "claude-cli",
            model="sonnet",
            structured_output=False,
            isolation=False,
            capabilities=ALL_CAPS,
        )
        self.assertNotIn("--safe-mode", no_isolation)
        self.assertNotIn("--json-schema", no_isolation)


# Trimmed from real `claude -p --output-format json` envelopes (CLI 2.1.173).
STRUCTURED_ENVELOPE = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "num_turns": 2,
    "result": "",
    "structured_output": {"status": "ok"},
    "session_id": "b3f54c12",
    "total_cost_usd": 0.003173,
    "usage": {
        "input_tokens": 1901,
        "cache_creation_input_tokens": 14,
        "cache_read_input_tokens": 7,
        "output_tokens": 70,
    },
    "modelUsage": {
        "claude-haiku-4-5-20251001": {
            "inputTokens": 2348,
            "outputTokens": 83,
            "costUSD": 0.003173,
            "contextWindow": 200000,
        }
    },
}

TEXT_ENVELOPE = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "num_turns": 1,
    "result": "```json\n{\"status\":\"ok\"}\n```",
    "session_id": "80c4e9a1",
    "total_cost_usd": 0.000979,
    "usage": {
        "input_tokens": 152,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 63,
    },
    "modelUsage": {
        "claude-haiku-4-5-20251001": {
            "inputTokens": 599,
            "outputTokens": 76,
            "costUSD": 0.000979,
        }
    },
}


class ClaudeEnvelopeParsingTests(unittest.TestCase):
    def test_structured_output_envelope_prefers_structured_payload(self):
        import json

        envelope = llm_backends._parse_claude_envelope(
            json.dumps(STRUCTURED_ENVELOPE)
        )
        self.assertEqual(envelope["structured"], {"status": "ok"})
        self.assertEqual(envelope["text"], "")
        self.assertEqual(envelope["input_tokens"], 1901)
        self.assertEqual(envelope["output_tokens"], 70)
        self.assertEqual(envelope["cache_creation_input_tokens"], 14)
        self.assertEqual(envelope["cache_read_input_tokens"], 7)
        self.assertEqual(envelope["total_cost_usd"], 0.003173)
        self.assertEqual(
            list(envelope["model_usage"]), ["claude-haiku-4-5-20251001"]
        )

    def test_text_envelope_keeps_fenced_result_for_extraction(self):
        import json

        envelope = llm_backends._parse_claude_envelope(json.dumps(TEXT_ENVELOPE))
        self.assertIsNone(envelope["structured"])
        self.assertIn("```json", envelope["text"])
        self.assertEqual(
            llm_backends.extract_json_from_text(envelope["text"]),
            {"status": "ok"},
        )

    def test_error_envelope_raises_runtime_error(self):
        import json

        payload = dict(TEXT_ENVELOPE, is_error=True, result="usage limit reached")
        with self.assertRaises(RuntimeError) as ctx:
            llm_backends._parse_claude_envelope(json.dumps(payload))
        self.assertIn("usage limit reached", str(ctx.exception))

    def test_non_json_stdout_raises_runtime_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            llm_backends._parse_claude_envelope("claude: command crashed")
        self.assertIn("non-JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

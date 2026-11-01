import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


llm_backends = load_module("llm_backends", "scripts/llm_backends.py")
port_skill = load_module("port_skill", "opencode/port_skill.py")

EVENTS = "\n".join(
    json.dumps(e)
    for e in [
        {"type": "step_start", "part": {"type": "step-start"}},
        {"type": "text", "part": {"type": "text", "text": '{"responses": {"ok": true}}'}},
        {
            "type": "step_finish",
            "part": {
                "type": "step-finish",
                "tokens": {"input": 120, "output": 30, "cache": {"read": 5, "write": 2}},
                "cost": 0.01,
            },
        },
    ]
)


class OpenCodeBackendTests(unittest.TestCase):
    def test_backend_is_selectable_and_marker_detected(self):
        self.assertIn("opencode-cli", llm_backends.BACKEND_CHOICES)
        self.assertIn("opencode-cli", llm_backends.REPORT_BACKEND_CHOICES)
        self.assertEqual(llm_backends.infer_backend_from_env({"OPENCODE": "1"}), "opencode-cli")

    def test_model_only_passed_in_provider_format(self):
        self.assertIsNone(llm_backends.resolve_model(None, "opencode-cli"))
        self.assertIsNone(llm_backends.resolve_model("sonnet", "opencode-cli"))
        self.assertEqual(
            llm_backends.resolve_model("ollama/qwen3:14b", "opencode-cli"), "ollama/qwen3:14b"
        )

    def test_command_gates_pure_flag(self):
        cmd = llm_backends._build_opencode_run_command(
            "ollama/x", capabilities={"--pure": True}
        )
        self.assertEqual(cmd[:6], ["opencode", "run", "--format", "json", "--agent", "persona-sim"])
        self.assertIn("--pure", cmd)
        self.assertEqual(cmd[-2:], ["-m", "ollama/x"])
        old = llm_backends._build_opencode_run_command(None, capabilities={"--pure": False})
        self.assertNotIn("--pure", old)
        self.assertNotIn("-m", old)

    def test_env_merges_agent_into_existing_inline_config(self):
        with mock.patch.dict("os.environ", {"OPENCODE_CONFIG_CONTENT": '{"model": "a/b"}'}):
            env = llm_backends._opencode_env("SYSTEM")
        inline = json.loads(env["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(inline["model"], "a/b")
        agent = inline["agent"]["persona-sim"]
        self.assertEqual(agent["prompt"], "SYSTEM")
        self.assertEqual(agent["tools"], {"*": False})
        self.assertEqual(env["OPENCODE_DISABLE_CLAUDE_CODE"], "1")

    def test_parse_events_collects_text_tokens_and_cost(self):
        parsed = llm_backends._parse_opencode_events(EVENTS)
        self.assertEqual(json.loads(parsed["text"]), {"responses": {"ok": True}})
        self.assertEqual(parsed["tokens"], {"input": 120, "output": 30, "cache_write": 2, "cache_read": 5})
        self.assertAlmostEqual(parsed["cost"], 0.01)

    def test_parse_events_raises_on_error_event(self):
        err = json.dumps({"type": "error", "error": {"name": "APIError", "data": {"message": "boom"}}})
        with self.assertRaisesRegex(RuntimeError, "boom"):
            llm_backends._parse_opencode_events(err)
        with self.assertRaises(RuntimeError):
            llm_backends._parse_opencode_events("not json")

    def test_text_completion_runs_subprocess(self):
        fake = subprocess.CompletedProcess([], 0, stdout=EVENTS, stderr="")
        with mock.patch.object(llm_backends, "backend_available", return_value=True), \
             mock.patch.object(llm_backends, "detect_opencode_capabilities", return_value={"--pure": True}), \
             mock.patch.object(llm_backends.subprocess, "run", return_value=fake) as run:
            result = llm_backends.run_text_completion(
                backend="opencode-cli", system_prompt="S", user_message="U"
            )
        self.assertEqual(result["backend"], "opencode-cli")
        self.assertEqual(result["input_tokens"], 120)
        self.assertEqual(run.call_args.kwargs["input"], "U")


class PortSkillTests(unittest.TestCase):
    def test_ported_skill_targets_opencode(self):
        text = (ROOT / "skills/persona/SKILL.md").read_text(encoding="utf-8")
        ported = port_skill.port(text, "/opt/oc/skills/persona")
        self.assertTrue(ported.startswith("---\nname: persona\n"))
        self.assertIn("compatibility: opencode", ported)
        self.assertNotIn("user-invokable", ported)
        self.assertNotIn("claude-cli", ported)
        self.assertNotIn("claude -p", ported)
        self.assertNotIn("python scripts/", ported)
        self.assertIn("python3 /opt/oc/skills/persona/scripts/simulate_survey.py", ported)
        self.assertIn("--backend opencode-cli", ported)

    def test_installer_is_offline_and_installs_skill_and_command(self):
        installer = (ROOT / "install-opencode.sh").read_text(encoding="utf-8")
        self.assertNotIn("git clone", installer)
        self.assertNotIn("curl", installer)
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ["bash", str(ROOT / "install-opencode.sh")],
                env={"PATH": "/usr/bin:/bin:" + str(Path(sys.executable).parent), "HOME": tmp,
                     "XDG_CONFIG_HOME": tmp},
                check=True, capture_output=True, text=True,
            )
            oc = Path(tmp) / "opencode"
            self.assertTrue((oc / "skills/persona/SKILL.md").is_file())
            self.assertTrue((oc / "skills/persona/scripts/simulate_survey.py").is_file())
            command = (oc / "commands/persona.md").read_text(encoding="utf-8")
            self.assertIn(str(oc / "skills/persona/SKILL.md"), command)
            self.assertIn("$ARGUMENTS", command)


if __name__ == "__main__":
    unittest.main()

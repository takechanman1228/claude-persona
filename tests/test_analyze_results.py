import json
import importlib.util
import tempfile
import unittest
import unittest.mock
from pathlib import Path


def load_module(module_name: str, relative_path: str):
    script_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


analyze_results = load_module("analyze_results", "scripts/analyze_results.py")


class NormalizeResultsTests(unittest.TestCase):
    def test_legacy_top_level_fields_are_normalized_into_responses(self):
        normalized = analyze_results.normalize_result_entry(
            {
                "name": "Ava Cole",
                "segment": "Budget Pragmatist",
                "age": 31,
                "gender": "Female",
                "occupation": "Industrial Designer",
                "preferred_option": "B",
                "reasoning": "Legacy top-level fields should still analyze correctly.",
            }
        )
        self.assertEqual(normalized["responses"]["preferred_option"], "B")
        self.assertEqual(
            normalized["responses"]["reasoning"],
            "Legacy top-level fields should still analyze correctly.",
        )


class DeterministicReportTests(unittest.TestCase):
    def test_usage_habits_report_includes_usage_specific_sections(self):
        results = analyze_results.normalize_results(
            [
                {
                    "name": "Ava Cole",
                    "segment": "Budget Pragmatist",
                    "age": 31,
                    "gender": "Female",
                    "occupation": "Industrial Designer",
                    "responses": {
                        "usage_frequency": {"Morning": "weekly", "At work": "daily"},
                        "current_product": "Olipop Variety Pack — around $9.99 for four cans.",
                        "purchase_channel": "Target — usually during my grocery run.",
                        "factor_ranking": {"Taste/flavor": 1, "Price": 2, "Health benefits": 3},
                        "pain_points": "Most functional sodas taste medicinal after the first few sips.",
                        "info_sources": ["Target aisle", "Friends"],
                    },
                },
                {
                    "name": "Marcus Hale",
                    "segment": "Health Optimizer",
                    "age": 42,
                    "gender": "Male",
                    "occupation": "Product Manager",
                    "responses": {
                        "usage_frequency": {"Afternoon": "daily", "With meals": "weekly"},
                        "current_product": "LaCroix Lime — about $5.99 for a 12-pack.",
                        "purchase_channel": "Trader Joe's.",
                        "factor_ranking": {"Ingredients/additives": 1, "Sugar content": 2, "Taste/flavor": 3},
                        "pain_points": "Claims are vague, and I have to work too hard to verify what is actually in the can.",
                        "info_sources": ["Ingredient labels", "Brand website"],
                    },
                },
            ]
        )
        df = analyze_results.flatten_responses(results)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            summary = analyze_results.analyze_usage_habits(results, df, output_dir, report_only=True)
            report = analyze_results.generate_markdown_report(
                results, df, summary, "usage-habits", output_dir
            )

        self.assertIn("## Usage Profiles", report)
        self.assertIn("Pain points:", report)
        self.assertIn("## Notable Verbatims", report)
        self.assertNotIn("No verbatim text was captured", report)
        self.assertIn("Target", summary["top_purchase_channels"])

    def test_price_summary_keeps_single_dollar_prefix(self):
        results = analyze_results.normalize_results(
            [
                {
                    "name": "Ava Cole",
                    "segment": "Budget Pragmatist",
                    "age": 31,
                    "gender": "Female",
                    "occupation": "Industrial Designer",
                    "responses": {
                        "max_wtp": 3,
                        "intent_by_price": {"$1.99": 4, "$2.49": 3},
                        "price_quality_preference": "cheaper",
                    },
                }
            ]
        )
        df = analyze_results.flatten_responses(results)

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = analyze_results.analyze_price_test(
                results, df, Path(tmpdir), report_only=True
            )

        self.assertEqual(summary["mean_intent_by_price"]["$1.99"], 4.0)
        self.assertEqual(summary["mean_intent_by_price"]["$2.49"], 3.0)

    def test_report_date_prefers_run_metadata_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            (output_dir / "run_metadata.json").write_text(
                '{"timestamp":"2026-03-16T12:34:56+00:00"}',
                encoding="utf-8",
            )

            self.assertEqual(
                analyze_results.resolve_report_date(output_dir),
                "2026-03-16",
            )

    def test_resolve_topic_prefers_run_metadata_topic(self):
        results = analyze_results.normalize_results(
            [
                {
                    "name": "Ava Cole",
                    "segment": "Budget Pragmatist",
                    "age": 31,
                    "gender": "Female",
                    "occupation": "Industrial Designer",
                    "responses": {
                        "preferred_option": "B",
                        "reasoning": "Support matters most.",
                    },
                }
            ]
        )
        df = analyze_results.flatten_responses(results)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            (output_dir / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "topic": "Explicit Topic",
                        "config_file": "demo/running-shoes/concept-test/config.json",
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                analyze_results._resolve_topic(output_dir, df),
                "Explicit Topic",
            )

    def test_resolve_topic_uses_relative_config_file_from_run_metadata(self):
        results = analyze_results.normalize_results(
            [
                {
                    "name": "Ava Cole",
                    "segment": "Budget Pragmatist",
                    "age": 31,
                    "gender": "Female",
                    "occupation": "Industrial Designer",
                    "responses": {
                        "preferred_option": "B",
                        "reasoning": "Support matters most.",
                    },
                }
            ]
        )
        df = analyze_results.flatten_responses(results)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            (output_dir / "run_metadata.json").write_text(
                json.dumps({"config_file": "demo/running-shoes/concept-test/config.json"}),
                encoding="utf-8",
            )

            self.assertEqual(
                analyze_results._resolve_topic(output_dir, df),
                "Running shoes",
            )

    def test_llm_report_fallback_keeps_explicit_topic(self):
        results = analyze_results.normalize_results(
            [
                {
                    "name": "Ava Cole",
                    "segment": "Budget Pragmatist",
                    "age": 31,
                    "gender": "Female",
                    "occupation": "Industrial Designer",
                    "responses": {
                        "preferred_option": "A",
                        "reasoning": "I need more specs before buying.",
                    },
                }
            ]
        )
        df = analyze_results.flatten_responses(results)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            summary = analyze_results.analyze_concept_test(
                results, df, output_dir, report_only=True
            )

            with unittest.mock.patch.object(
                analyze_results,
                "run_text_completion",
                side_effect=RuntimeError("forced failure"),
            ):
                report = analyze_results.generate_llm_report(
                    results,
                    df,
                    summary,
                    "concept-test",
                    output_dir,
                    backend="codex-cli",
                    topic="User Supplied Topic",
                )

        self.assertIn(
            "# Concept Test: User Supplied Topic — Virtual Research Report",
            report,
        )


class ReportPromptDispatchTests(unittest.TestCase):
    """Survey-type-specific LLM report prompts must be wired through generate_llm_report."""

    def _build_minimal_fixture(self, responses: dict, output_dir: Path):
        results = analyze_results.normalize_results(
            [
                {
                    "name": "Ava Cole",
                    "segment": "Budget Pragmatist",
                    "age": 31,
                    "gender": "Female",
                    "occupation": "Industrial Designer",
                    "responses": responses,
                }
            ]
        )
        df = analyze_results.flatten_responses(results)
        return results, df

    def _capture_system_prompt(self, survey_type: str, responses: dict):
        captured = {}

        def _fake(*_args, system_prompt: str, **_kwargs):
            captured["system_prompt"] = system_prompt
            return {"text": "# captured"}

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            results, df = self._build_minimal_fixture(responses, output_dir)
            summary = {"total_respondents": len(results)}
            with unittest.mock.patch.object(
                analyze_results, "run_text_completion", side_effect=_fake
            ):
                analyze_results.generate_llm_report(
                    results,
                    df,
                    summary,
                    survey_type,
                    output_dir,
                    backend="codex-cli",
                    topic="Test Topic",
                )
        return captured.get("system_prompt", "")

    def test_ask_survey_uses_ask_prompt(self):
        prompt = self._capture_system_prompt(
            "ask",
            {
                "short_answer": "Something",
                "reasoning": "Because",
                "themes": ["a"],
                "emotion": "frustrated",
            },
        )
        self.assertIn("Ask:", prompt)
        self.assertIn("Where They Agreed", prompt)
        self.assertIn("Where They Differed", prompt)
        self.assertIn("Top Signals", prompt)
        self.assertNotIn("Preference Verdict", prompt)

    def test_concept_test_uses_concept_test_prompt(self):
        prompt = self._capture_system_prompt(
            "concept-test",
            {"preferred_option": "A", "reasoning": "Simple.", "purchase_likelihood": 4},
        )
        self.assertIn("Preference Verdict", prompt)
        self.assertIn("Segment / Profile Splits", prompt)
        self.assertIn("Improvement Theme Clusters", prompt)
        self.assertIn("Per-Concept Strengths and Weaknesses", prompt)
        self.assertNotIn("Where They Agreed", prompt)

    def test_unknown_survey_type_falls_back_to_generic_prompt(self):
        prompt = self._capture_system_prompt(
            "brand-map",
            {"unaided_awareness": ["A", "B"]},
        )
        self.assertIn("[Survey Type]", prompt)
        self.assertNotIn("Preference Verdict", prompt)
        self.assertNotIn("Where They Agreed", prompt)

    def test_select_report_system_prompt_dispatch(self):
        self.assertIs(
            analyze_results._select_report_system_prompt("ask"),
            analyze_results.ASK_REPORT_SYSTEM_PROMPT,
        )
        self.assertIs(
            analyze_results._select_report_system_prompt("concept-test"),
            analyze_results.CONCEPT_TEST_REPORT_SYSTEM_PROMPT,
        )
        self.assertIs(
            analyze_results._select_report_system_prompt("brand-map"),
            analyze_results.GENERIC_REPORT_SYSTEM_PROMPT,
        )


class FindingsAndTruncationTests(unittest.TestCase):
    """_extract_findings must not pad with filler; _truncate must respect sentence boundaries."""

    def test_extract_findings_no_panel_size_filler(self):
        results = analyze_results.normalize_results(
            [
                {
                    "name": "Ava",
                    "segment": "X",
                    "age": 31,
                    "gender": "F",
                    "occupation": "Designer",
                    "responses": {
                        "themes": ["greenwashing", "price sensitivity"],
                        "emotion": "frustrated",
                    },
                },
                {
                    "name": "Bo",
                    "segment": "Y",
                    "age": 28,
                    "gender": "M",
                    "occupation": "Engineer",
                    "responses": {
                        "themes": ["greenwashing", "ingredient opacity"],
                        "emotion": "exasperated",
                    },
                },
            ]
        )
        df = analyze_results.flatten_responses(results)
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = analyze_results.analyze_ask(results, df, Path(tmpdir), report_only=True)
        findings = analyze_results._extract_findings(df, summary, "ask")
        joined = " | ".join(findings)
        self.assertNotIn("Panel size is", joined)
        self.assertNotIn("Panel covers", joined)

    def test_truncate_under_limit_returns_text_unchanged(self):
        text = "Short complete sentence."
        self.assertEqual(analyze_results._truncate(text, 600, sentence_aware=True), text)

    def test_truncate_sentence_aware_stops_at_period(self):
        text = (
            "First sentence about greenwashing claims and why they erode trust. "
            "Second sentence continues into detail that exceeds the simple limit and should be cut."
        )
        truncated = analyze_results._truncate(text, 90, sentence_aware=True)
        self.assertTrue(truncated.endswith("."))
        self.assertNotIn("...", truncated)
        self.assertLess(len(truncated), len(text))

    def test_truncate_hard_cut_when_no_sentence_boundary_in_window(self):
        text = "word " * 200
        truncated = analyze_results._truncate(text, 40, sentence_aware=True)
        self.assertTrue(truncated.endswith("..."))
        self.assertLessEqual(len(truncated), 40)


if __name__ == "__main__":
    unittest.main()

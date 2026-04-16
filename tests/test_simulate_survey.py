import importlib.util
import unittest
from pathlib import Path


def load_module(module_name: str, relative_path: str):
    script_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


simulate_survey = load_module("simulate_survey", "scripts/simulate_survey.py")


class ValidateResponseTests(unittest.TestCase):
    def test_accepts_canonical_nested_concept_response(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "preferred_option": "A",
                    "reasoning": "This fits my routine better than the alternatives.",
                }
            },
            "concept-test",
            allowed_options={"A", "B", "C"},
        )
        self.assertEqual(issues, [])

    def test_rejects_top_level_only_concept_response(self):
        issues = simulate_survey.validate_response(
            {
                "preferred_option": "A",
                "reasoning": "Top-level only should fail validation now.",
            },
            "concept-test",
        )
        self.assertIn("Missing or invalid 'responses' field", issues)
        self.assertIn("Missing 'preferred_option' in responses", issues)
        self.assertIn("Missing 'reasoning' in responses", issues)

    def test_extracts_allowed_concept_options_from_markdown(self):
        options = simulate_survey.extract_allowed_concept_options(
            {
                "concepts": (
                    "**A: Lightweight Comfort** — Built for speed.\n\n"
                    "**B: Soft Cushion Support** — Built for protection.\n\n"
                    "**C: Versatile Style** — Built for lifestyle."
                )
            }
        )
        self.assertEqual(options, {"A", "B", "C"})

    def test_rejects_invalid_preferred_option_value(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "preferred_option": "Concept B",
                    "reasoning": "I like the supportive positioning.",
                }
            },
            "concept-test",
            allowed_options={"A", "B", "C"},
        )
        self.assertIn("Invalid 'preferred_option' in responses", issues)

    def test_rejects_blank_reasoning_for_concept_test(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "preferred_option": "B",
                    "reasoning": "   ",
                }
            },
            "concept-test",
            allowed_options={"A", "B", "C"},
        )
        self.assertIn("Invalid 'reasoning' in responses", issues)

    def test_accepts_brand_map_response_shape(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "unaided_awareness": ["Olipop", "Poppi"],
                    "aided_familiarity": {
                        "Olipop": "know_well",
                        "Poppi": "heard_of",
                    },
                    "brand_buckets": {
                        "like": ["Olipop"],
                        "dislike": [],
                        "neutral": ["Poppi"],
                    },
                    "consideration_set": ["Olipop", "Poppi"],
                    "brand_associations": {
                        "Olipop": "Feels premium and health-forward.",
                    },
                }
            },
            "brand-map",
        )
        self.assertEqual(issues, [])

    def test_rejects_brand_map_invalid_bucket_shape(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "unaided_awareness": ["Olipop"],
                    "aided_familiarity": {"Olipop": "favorite"},
                    "brand_buckets": {
                        "like": ["Olipop"],
                        "dislike": [],
                    },
                    "consideration_set": ["Olipop"],
                    "brand_associations": {"Olipop": "Health halo."},
                }
            },
            "brand-map",
        )
        self.assertIn("Invalid 'aided_familiarity' in responses", issues)
        self.assertIn("Invalid 'brand_buckets' in responses", issues)

    def test_accepts_price_test_response_shape(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "max_wtp": 3.49,
                    "intent_by_price": {"$2.49": 4, "$3.49": 3},
                    "value_perception": "The lower price feels safe. The higher price needs a stronger proof point.",
                    "competitive_reference": 2.99,
                    "price_quality_preference": "depends",
                    "reasoning": "I would pay more if the ingredients feel justified.",
                }
            },
            "price-test",
        )
        self.assertEqual(issues, [])

    def test_rejects_price_test_invalid_numeric_and_enum_values(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "max_wtp": 0,
                    "intent_by_price": {"$2.49": 7},
                    "value_perception": "   ",
                    "competitive_reference": "maybe",
                    "price_quality_preference": "premium",
                    "reasoning": "",
                }
            },
            "price-test",
        )
        self.assertIn("Invalid 'max_wtp' in responses", issues)
        self.assertIn("Invalid 'intent_by_price' in responses", issues)
        self.assertIn("Invalid 'value_perception' in responses", issues)
        self.assertIn("Invalid 'competitive_reference' in responses", issues)
        self.assertIn("Invalid 'price_quality_preference' in responses", issues)
        self.assertIn("Invalid 'reasoning' in responses", issues)

    def test_accepts_usage_habits_response_shape(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "usage_frequency": {"Morning": "daily", "At work": "weekly"},
                    "current_product": "Olipop Strawberry Vanilla, around $2.79 per can.",
                    "purchase_channel": "Target",
                    "factor_ranking": {"Taste": 1, "Price": 2, "Ingredients": 3},
                    "pain_points": "Too many brands taste medicinal after the first few sips.",
                    "info_sources": ["Friends", "Online reviews"],
                }
            },
            "usage-habits",
        )
        self.assertEqual(issues, [])

    def test_rejects_usage_habits_invalid_frequency_and_ranking(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "usage_frequency": {"Morning": "hourly"},
                    "current_product": " ",
                    "purchase_channel": "",
                    "factor_ranking": {"Taste": 1, "Price": 1},
                    "pain_points": "",
                    "info_sources": [],
                }
            },
            "usage-habits",
        )
        self.assertIn("Invalid 'usage_frequency' in responses", issues)
        self.assertIn("Invalid 'current_product' in responses", issues)
        self.assertIn("Invalid 'purchase_channel' in responses", issues)
        self.assertIn("Invalid 'factor_ranking' in responses", issues)
        self.assertIn("Invalid 'pain_points' in responses", issues)
        self.assertIn("Invalid 'info_sources' in responses", issues)


class ValidateAskResponseTests(unittest.TestCase):
    def test_accepts_valid_ask_response(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "short_answer": "I would ignore it because it feels generic and impersonal.",
                    "reasoning": "The ad doesn't speak to my specific training goals. It looks like it was designed for everyone, which means it resonates with no one.",
                    "themes": ["generic messaging", "irrelevant targeting", "no proof point"],
                    "emotion": "indifferent",
                }
            },
            "ask",
        )
        self.assertEqual(issues, [])

    def test_accepts_ask_response_without_optional_fields(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "short_answer": "Sizing uncertainty is the biggest friction point for me.",
                    "reasoning": "I cannot try shoes on before buying. Returns are a hassle and I have been burned before.",
                }
            },
            "ask",
        )
        self.assertEqual(issues, [])

    def test_rejects_missing_short_answer(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "reasoning": "Some reasoning here.",
                }
            },
            "ask",
        )
        self.assertIn("Missing 'short_answer' in responses", issues)

    def test_rejects_missing_reasoning(self):
        issues = simulate_survey.validate_response(
            {
                "responses": {
                    "short_answer": "I find it frustrating.",
                }
            },
            "ask",
        )
        self.assertIn("Missing 'reasoning' in responses", issues)

    def test_rejects_top_level_ask_response(self):
        issues = simulate_survey.validate_response(
            {
                "short_answer": "I would ignore it.",
                "reasoning": "Too generic.",
            },
            "ask",
        )
        self.assertIn("Missing or invalid 'responses' field", issues)
        self.assertIn("Missing 'short_answer' in responses", issues)
        self.assertIn("Missing 'reasoning' in responses", issues)


class AssembleResultsTests(unittest.TestCase):
    def test_persona_metadata_is_source_of_truth(self):
        api_results = [
            {
                "persona_name": "Ava Cole",
                "success": True,
                "response": {
                    "name": "Wrong Name",
                    "segment": "Wrong Segment",
                    "age": 99,
                    "gender": "Unknown",
                    "occupation": "Wrong Occupation",
                    "responses": {
                        "preferred_option": "B",
                        "reasoning": "The persona metadata should come from the saved panel.",
                    },
                },
            }
        ]
        personas = [
            {
                "segment": "Budget Pragmatist",
                "persona": {
                    "name": "Ava Cole",
                    "age": 31,
                    "gender": "Female",
                    "occupation": {"title": "Industrial Designer"},
                },
            }
        ]

        results = simulate_survey.assemble_results(api_results, personas)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Ava Cole")
        self.assertEqual(results[0]["segment"], "Budget Pragmatist")
        self.assertEqual(results[0]["age"], 31)
        self.assertEqual(results[0]["gender"], "Female")
        self.assertEqual(results[0]["occupation"], "Industrial Designer")
        self.assertNotIn("preferred_option", results[0])
        self.assertNotIn("reasoning", results[0])


class RuntimeConfigTests(unittest.TestCase):
    def test_resolve_runtime_settings_keeps_codex_model_optional(self):
        config = {
            "backend": "codex-cli",
            "report_backend": "same",
        }

        with unittest.mock.patch.object(
            simulate_survey,
            "resolve_backend",
            return_value="codex-cli",
        ):
            resolved = simulate_survey.resolve_runtime_settings(config)

        self.assertEqual(resolved["_resolved_backend"], "codex-cli")
        self.assertIsNone(resolved["_resolved_model"])
        self.assertEqual(resolved["_resolved_report_backend"], "codex-cli")
        self.assertIsNone(resolved["_resolved_report_model"])


class RunMetadataTests(unittest.TestCase):
    def test_usage_fields_become_null_when_backend_has_no_usage_metadata(self):
        metadata = simulate_survey.build_run_metadata(
            {
                "_resolved_backend": "codex-cli",
                "_resolved_model": None,
                "_config_path": "demo.json",
            },
            [
                {
                    "persona_name": "Ava Cole",
                    "success": True,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "latency_ms": 123,
                    "attempts": 1,
                    "adherence_score": None,
                    "adherence_passed": None,
                    "adherence_retried": False,
                    "validation_issues": [],
                    "error": None,
                    "usage_supported": False,
                }
            ],
            total_elapsed_ms=456,
        )

        self.assertEqual(metadata["backend"], "codex-cli")
        self.assertFalse(metadata["usage_supported"])
        self.assertIsNone(metadata["total_input_tokens"])
        self.assertIsNone(metadata["total_output_tokens"])
        self.assertIsNone(metadata["total_tokens"])
        self.assertIsNone(metadata["per_persona"][0]["input_tokens"])

    def test_preflight_failure_stage_is_recorded_in_metadata(self):
        metadata = simulate_survey.build_run_metadata(
            {
                "_resolved_backend": "codex-cli",
                "_resolved_model": None,
                "_config_path": "demo.json",
            },
            [],
            total_elapsed_ms=321,
            preflight_result={
                "success": False,
                "backend": "codex-cli",
                "resolved_model": None,
                "check": "minimal-json-completion",
                "usage_supported": False,
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms": 87,
                "error": "network unreachable",
            },
            failure_stage="preflight",
        )

        self.assertEqual(metadata["failure_stage"], "preflight")
        self.assertEqual(metadata["preflight"]["backend"], "codex-cli")
        self.assertFalse(metadata["preflight"]["success"])
        self.assertEqual(metadata["preflight"]["error"], "network unreachable")

    def test_config_file_is_repo_relative_and_topic_is_preserved(self):
        metadata = simulate_survey.build_run_metadata(
            {
                "_resolved_backend": "claude-cli",
                "_resolved_model": "sonnet",
                "_config_path": str(
                    simulate_survey.SKILL_DIR
                    / "demo"
                    / "running-shoes"
                    / "concept-test"
                    / "config.json"
                ),
                "topic": "Running shoes",
            },
            [],
            total_elapsed_ms=123,
        )

        self.assertEqual(
            metadata["config_file"],
            "demo/running-shoes/concept-test/config.json",
        )
        self.assertEqual(metadata["topic"], "Running shoes")

    def test_adherence_metadata_distinguishes_first_pass_and_retry_pass(self):
        metadata = simulate_survey.build_run_metadata(
            {
                "_resolved_backend": "claude-cli",
                "_resolved_model": "sonnet",
                "_config_path": "demo.json",
            },
            [
                {
                    "persona_name": "Ava Cole",
                    "success": True,
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "latency_ms": 10,
                    "attempts": 1,
                    "first_adherence_score": 8,
                    "first_adherence_passed": True,
                    "adherence_score": 8,
                    "adherence_passed": True,
                    "adherence_retried": False,
                    "validation_issues": [],
                    "error": None,
                    "usage_supported": True,
                },
                {
                    "persona_name": "Ben Hart",
                    "success": True,
                    "input_tokens": 1,
                    "output_tokens": 1,
                    "latency_ms": 12,
                    "attempts": 1,
                    "first_adherence_score": 6,
                    "first_adherence_passed": False,
                    "adherence_score": 8,
                    "adherence_passed": True,
                    "adherence_retried": True,
                    "validation_issues": [],
                    "error": None,
                    "usage_supported": True,
                },
            ],
            total_elapsed_ms=50,
        )

        self.assertEqual(metadata["adherence_checks"]["total_checked"], 2)
        self.assertEqual(metadata["adherence_checks"]["passed_first_try"], 1)
        self.assertEqual(metadata["adherence_checks"]["passed_after_retry"], 1)
        self.assertEqual(
            metadata["per_persona"][1]["first_adherence_passed"],
            False,
        )
        self.assertEqual(metadata["per_persona"][1]["adherence_passed"], True)


if __name__ == "__main__":
    unittest.main()

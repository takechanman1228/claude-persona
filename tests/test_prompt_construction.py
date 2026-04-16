import importlib.util
import json
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

SAMPLE_PROFILE = {
    "name": "Marcus Chen",
    "age": 32,
    "gender": "Male",
    "occupation": "Senior Software Engineer",
}


class SubstituteVariablesTests(unittest.TestCase):
    def test_replaces_placeholder(self):
        result = simulate_survey.substitute_variables(
            "Category: {{category}}", {"category": "Running shoes"}
        )
        self.assertEqual(result, "Category: Running shoes")

    def test_multiple_placeholders(self):
        template = "{{greeting}}, {{name}}!"
        result = simulate_survey.substitute_variables(
            template, {"greeting": "Hello", "name": "World"}
        )
        self.assertEqual(result, "Hello, World!")

    def test_missing_placeholder_left_unchanged(self):
        result = simulate_survey.substitute_variables(
            "Value: {{missing}}", {"other": "data"}
        )
        self.assertEqual(result, "Value: {{missing}}")

    def test_non_string_values_converted(self):
        result = simulate_survey.substitute_variables(
            "Count: {{n}}", {"n": 42}
        )
        self.assertEqual(result, "Count: 42")


class BuildSinglePersonaPromptTests(unittest.TestCase):
    def test_replaces_multi_persona_instruction(self):
        simulation_prompt = (
            "You will role-play as multiple\n"
            "personas, answering survey questions AS each person would."
        )
        result = simulate_survey.build_single_persona_prompt(
            simulation_prompt=simulation_prompt,
            survey_template="Questions here.",
            persona_profile=SAMPLE_PROFILE,
            variables={},
        )
        self.assertIn("one specific consumer", result)
        self.assertNotIn("multiple\npersonas", result)

    def test_persona_json_embedded(self):
        simulation_prompt = "## Persona Definitions\n\n{PERSONAS_JSON}"
        result = simulate_survey.build_single_persona_prompt(
            simulation_prompt=simulation_prompt,
            survey_template="",
            persona_profile=SAMPLE_PROFILE,
            variables={},
        )
        self.assertIn("## Your Persona", result)
        self.assertIn('"Marcus Chen"', result)
        parsed = json.loads(result.split("## Your Persona\n\n")[1])
        self.assertEqual(parsed["name"], "Marcus Chen")

    def test_survey_questions_substituted(self):
        simulation_prompt = "Questions: {SURVEY_QUESTIONS}"
        result = simulate_survey.build_single_persona_prompt(
            simulation_prompt=simulation_prompt,
            survey_template="Rate {{category}} on a 1-5 scale.",
            persona_profile=SAMPLE_PROFILE,
            variables={"category": "running shoes"},
        )
        self.assertIn("Rate running shoes on a 1-5 scale.", result)

    def test_concepts_from_variables(self):
        simulation_prompt = "Concepts: {CONCEPTS}"
        result = simulate_survey.build_single_persona_prompt(
            simulation_prompt=simulation_prompt,
            survey_template="",
            persona_profile=SAMPLE_PROFILE,
            variables={"concepts": "**A: Speed** — Fast\n**B: Comfort** — Soft"},
        )
        self.assertIn("**A: Speed**", result)

    def test_concepts_fallback_to_product_description(self):
        simulation_prompt = "Concepts: {CONCEPTS}"
        result = simulate_survey.build_single_persona_prompt(
            simulation_prompt=simulation_prompt,
            survey_template="",
            persona_profile=SAMPLE_PROFILE,
            variables={"product_description": "A new running shoe"},
        )
        self.assertIn("A new running shoe", result)

    def test_concepts_fallback_to_na(self):
        simulation_prompt = "Concepts: {CONCEPTS}"
        result = simulate_survey.build_single_persona_prompt(
            simulation_prompt=simulation_prompt,
            survey_template="",
            persona_profile=SAMPLE_PROFILE,
            variables={},
        )
        self.assertIn("N/A", result)

    def test_unicode_persona_preserved(self):
        profile = {"name": "田中ゆき", "age": 28}
        simulation_prompt = "## Persona Definitions\n\n{PERSONAS_JSON}"
        result = simulate_survey.build_single_persona_prompt(
            simulation_prompt=simulation_prompt,
            survey_template="",
            persona_profile=profile,
            variables={},
        )
        self.assertIn("田中ゆき", result)


class LoadSimulationPromptTests(unittest.TestCase):
    def test_loads_prompt_from_file(self):
        prompt = simulate_survey.load_simulation_prompt()
        self.assertIsInstance(prompt, str)
        self.assertTrue(len(prompt) > 100)

    def test_prompt_contains_expected_placeholders(self):
        prompt = simulate_survey.load_simulation_prompt()
        self.assertIn("{PERSONAS_JSON}", prompt)
        self.assertIn("{SURVEY_QUESTIONS}", prompt)


class LoadSurveyTemplateTests(unittest.TestCase):
    def test_loads_concept_test_template(self):
        template = simulate_survey.load_survey_template("concept-test")
        self.assertIsInstance(template, str)
        self.assertTrue(len(template) > 50)

    def test_invalid_survey_type_raises_key_error(self):
        with self.assertRaises(KeyError):
            simulate_survey.load_survey_template("nonexistent-type")


if __name__ == "__main__":
    unittest.main()

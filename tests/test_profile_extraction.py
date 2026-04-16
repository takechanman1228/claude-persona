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


# ─── Minimal persona fixture ────────────────────────────────────────────────

FULL_PERSONA = {
    "persona": {
        "name": "Marcus Chen",
        "age": 32,
        "gender": "Male",
        "occupation": {
            "title": "Senior Software Engineer",
            "organization": "Stripe",
        },
        "residence": "Seattle, WA",
        "education": "B.S. Computer Science, University of Washington. Graduated with honors.",
        "style": "Terse and metric-forward; bullet points.",
        "personality": {
            "big_five": {
                "openness": 0.45,
                "conscientiousness": 0.95,
                "extraversion": 0.25,
                "agreeableness": 0.2,
                "neuroticism": 0.2,
            },
            "traits": [
                "analytical",
                "disciplined",
                "competitive",
                "introverted",
                "exacting",
                "meticulous",
            ],
        },
        "preferences": {
            "interests": [
                "marathon racing",
                "running biomechanics",
                "wearable fitness tech",
                "strength training for runners",
                "nutrition periodization",
                "data visualization",
                "competitive cycling",
            ],
            "likes": [
                "carbon-fiber plate shoes under 200g",
                "GPS splits accurate to 0.01 miles",
                "peer-reviewed sports science papers",
                "post-run recovery protocols",
                "minimalist product design",
            ],
            "dislikes": [
                "marketing buzzwords",
                "cushion-heavy shoes",
                "group runs slower than easy pace",
            ],
        },
        "beliefs": [
            "Every variable is measurable",
            "Shoe weight correlates with race performance",
            "Recovery is training",
            "Consumer marketing lies",
        ],
    },
    "segment": "Performance Purist",
    "segment_id": 1,
}


class FirstSentenceTests(unittest.TestCase):
    def test_extracts_first_sentence(self):
        text = "Graduated from University of Washington. Then worked at Google."
        self.assertEqual(
            simulate_survey.first_sentence(text),
            "Graduated from University of Washington.",
        )

    def test_returns_full_text_when_no_period(self):
        self.assertEqual(simulate_survey.first_sentence("No period here"), "No period here")

    def test_returns_empty_on_empty_input(self):
        self.assertEqual(simulate_survey.first_sentence(""), "")

    def test_handles_single_period_at_end(self):
        self.assertEqual(simulate_survey.first_sentence("One sentence."), "One sentence.")


class ScoreRelevanceTests(unittest.TestCase):
    def test_two_word_overlap_scores_three(self):
        topic_words = {"running", "shoes"}
        score = simulate_survey._score_relevance("running shoes review", topic_words)
        self.assertEqual(score, 3)

    def test_one_word_overlap_scores_two(self):
        topic_words = {"running", "shoes"}
        score = simulate_survey._score_relevance("competitive running", topic_words)
        self.assertEqual(score, 2)

    def test_no_overlap_scores_one(self):
        topic_words = {"running", "shoes"}
        score = simulate_survey._score_relevance("data visualization", topic_words)
        self.assertEqual(score, 1)

    def test_case_insensitive(self):
        topic_words = {"running"}
        score = simulate_survey._score_relevance("RUNNING marathon", topic_words)
        self.assertEqual(score, 2)

    def test_empty_topic_words_scores_one(self):
        score = simulate_survey._score_relevance("anything", set())
        self.assertEqual(score, 1)


class SelectRelevantTests(unittest.TestCase):
    def test_no_topic_returns_first_n(self):
        items = ["a", "b", "c", "d", "e", "f"]
        result = simulate_survey._select_relevant(items, "", 3)
        self.assertEqual(result, ["a", "b", "c"])

    def test_topic_reorders_by_relevance(self):
        items = ["data visualization", "marathon racing", "running biomechanics"]
        result = simulate_survey._select_relevant(items, "running shoes", 3)
        # "running biomechanics" has 1 overlap → score 2
        # "marathon racing" has 0 overlap → score 1
        # "data visualization" has 0 overlap → score 1
        self.assertEqual(result[0], "running biomechanics")

    def test_empty_items_returns_empty(self):
        self.assertEqual(simulate_survey._select_relevant([], "topic", 5), [])

    def test_fewer_items_than_n_returns_all(self):
        items = ["a", "b"]
        result = simulate_survey._select_relevant(items, "", 5)
        self.assertEqual(result, ["a", "b"])


class ExtractSimulationProfileTests(unittest.TestCase):
    def test_basic_field_extraction(self):
        profile = simulate_survey.extract_simulation_profile(FULL_PERSONA)
        self.assertEqual(profile["name"], "Marcus Chen")
        self.assertEqual(profile["age"], 32)
        self.assertEqual(profile["gender"], "Male")
        self.assertEqual(profile["occupation"], "Senior Software Engineer")
        self.assertEqual(profile["organization"], "Stripe")
        self.assertEqual(profile["residence"], "Seattle, WA")
        self.assertEqual(profile["segment"], "Performance Purist")
        self.assertEqual(profile["segment_id"], 1)

    def test_education_first_sentence_only(self):
        profile = simulate_survey.extract_simulation_profile(FULL_PERSONA)
        # first_sentence splits on period+space; "B.S. " matches first
        self.assertEqual(profile["education"], "B.S.")

    def test_traits_capped_at_five(self):
        profile = simulate_survey.extract_simulation_profile(FULL_PERSONA)
        self.assertEqual(len(profile["personality"]["traits"]), 5)
        self.assertNotIn("meticulous", profile["personality"]["traits"])

    def test_beliefs_capped_at_three(self):
        profile = simulate_survey.extract_simulation_profile(FULL_PERSONA)
        self.assertEqual(len(profile["beliefs"]), 3)
        self.assertNotIn("Consumer marketing lies", profile["beliefs"])

    def test_interests_capped_at_five(self):
        profile = simulate_survey.extract_simulation_profile(FULL_PERSONA)
        self.assertEqual(len(profile["interests"]), 5)

    def test_big_five_preserved(self):
        profile = simulate_survey.extract_simulation_profile(FULL_PERSONA)
        self.assertEqual(profile["personality"]["big_five"]["conscientiousness"], 0.95)

    def test_style_never_truncated(self):
        profile = simulate_survey.extract_simulation_profile(FULL_PERSONA)
        self.assertEqual(profile["style"], "Terse and metric-forward; bullet points.")

    def test_topic_relevance_reorders_interests(self):
        profile = simulate_survey.extract_simulation_profile(
            FULL_PERSONA, topic="running shoes"
        )
        # "running biomechanics" has overlap with "running" → should rank higher
        self.assertIn("running biomechanics", profile["interests"])

    def test_missing_optional_fields_use_defaults(self):
        minimal = {
            "persona": {
                "name": "Test Person",
                "age": 25,
                "gender": "Female",
                "occupation": {"title": "Analyst"},
                "personality": {
                    "big_five": {
                        "openness": 0.5,
                        "conscientiousness": 0.5,
                        "extraversion": 0.5,
                        "agreeableness": 0.5,
                        "neuroticism": 0.5,
                    },
                },
            },
        }
        profile = simulate_survey.extract_simulation_profile(minimal)
        self.assertEqual(profile["organization"], "")
        self.assertEqual(profile["residence"], "")
        self.assertEqual(profile["education"], "")
        self.assertEqual(profile["style"], "")
        self.assertEqual(profile["interests"], [])
        self.assertEqual(profile["likes"], [])
        self.assertEqual(profile["dislikes"], [])
        self.assertEqual(profile["beliefs"], [])
        self.assertEqual(profile["segment"], "")
        self.assertIsNone(profile["segment_id"])
        self.assertEqual(profile["personality"]["traits"], [])


if __name__ == "__main__":
    unittest.main()

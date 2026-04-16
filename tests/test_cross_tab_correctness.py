import csv
import importlib.util
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path


def load_module(module_name: str, relative_path: str):
    script_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


analyze_results = load_module("analyze_results", "scripts/analyze_results.py")

SKILL_DIR = Path(__file__).resolve().parents[1]
DEMO_RESULTS_PATH = (
    SKILL_DIR / "demo" / "running-shoes" / "concept-test" / "results" / "results.json"
)
DEMO_SUMMARY_PATH = (
    SKILL_DIR / "demo" / "running-shoes" / "concept-test" / "results" / "summary.json"
)


class CrossTabCorrectnessTests(unittest.TestCase):
    def test_demo_summary_matches_results_json(self):
        results = json.loads(DEMO_RESULTS_PATH.read_text(encoding="utf-8"))
        summary = json.loads(DEMO_SUMMARY_PATH.read_text(encoding="utf-8"))

        expected_segments = Counter(result["segment"] for result in results)
        expected_preferences = Counter(
            result["responses"]["preferred_option"]
            for result in results
        )
        purchase_likelihoods = [
            float(result["responses"]["purchase_likelihood"])
            for result in results
        ]
        expected_purchase_summary = {
            "mean": round(sum(purchase_likelihoods) / len(purchase_likelihoods), 2),
            "median": round(sorted(purchase_likelihoods)[len(purchase_likelihoods) // 2], 2),
            "min": round(min(purchase_likelihoods), 2),
            "max": round(max(purchase_likelihoods), 2),
        }

        self.assertEqual(summary["total_respondents"], len(results))
        self.assertEqual(summary["segments"], dict(expected_segments))
        self.assertEqual(summary["overall_preference"], dict(expected_preferences))
        self.assertEqual(summary["purchase_likelihood"], expected_purchase_summary)

    def test_non_degenerate_concept_analysis_writes_cross_tabs_and_percentages(self):
        results = analyze_results.normalize_results(
            [
                {
                    "name": "Ava Cole",
                    "segment": "Budget Pragmatists",
                    "age": 31,
                    "gender": "Female",
                    "occupation": "Industrial Designer",
                    "responses": {
                        "preferred_option": "A",
                        "reasoning": "Value wins.",
                        "purchase_likelihood": 3,
                    },
                },
                {
                    "name": "Marcus Hale",
                    "segment": "Budget Pragmatists",
                    "age": 42,
                    "gender": "Male",
                    "occupation": "Product Manager",
                    "responses": {
                        "preferred_option": "A",
                        "reasoning": "It is the most efficient option.",
                        "purchase_likelihood": 4,
                    },
                },
                {
                    "name": "Jules Park",
                    "segment": "Budget Pragmatists",
                    "age": 29,
                    "gender": "Non-binary",
                    "occupation": "Consultant",
                    "responses": {
                        "preferred_option": "B",
                        "reasoning": "Support matters more here.",
                        "purchase_likelihood": 2,
                    },
                },
                {
                    "name": "Diana Frost",
                    "segment": "Comfort Seekers",
                    "age": 51,
                    "gender": "Female",
                    "occupation": "Teacher",
                    "responses": {
                        "preferred_option": "B",
                        "reasoning": "I need cushioning first.",
                        "purchase_likelihood": 4,
                    },
                },
            ]
        )
        df = analyze_results.flatten_responses(results)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            summary = analyze_results.analyze_concept_test(
                results, df, output_dir, report_only=True
            )

            cross_tab_path = output_dir / "cross_tabs.csv"
            cross_pct_path = output_dir / "cross_tabs_pct.csv"

            self.assertTrue(cross_tab_path.exists())
            self.assertTrue(cross_pct_path.exists())
            self.assertFalse((output_dir / "persona_comparison.csv").exists())
            self.assertEqual(summary["overall_preference"], {"A": 2, "B": 2})

            with cross_tab_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                index_col = reader.fieldnames[0]
                rows = {row[index_col]: row for row in reader}

            self.assertEqual(rows["Budget Pragmatists"]["A"], "2")
            self.assertEqual(rows["Budget Pragmatists"]["B"], "1")
            self.assertEqual(rows["Comfort Seekers"]["A"], "0")
            self.assertEqual(rows["Comfort Seekers"]["B"], "1")
            self.assertEqual(rows["All"]["A"], "2")
            self.assertEqual(rows["All"]["B"], "2")

            with cross_pct_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                index_col = reader.fieldnames[0]
                rows = {row[index_col]: row for row in reader}

            self.assertEqual(rows["Budget Pragmatists"]["A"], "66.7")
            self.assertEqual(rows["Budget Pragmatists"]["B"], "33.3")
            self.assertEqual(rows["Comfort Seekers"]["B"], "100.0")

    def test_degenerate_demo_analysis_writes_persona_comparison_instead_of_cross_tabs(self):
        results = json.loads(DEMO_RESULTS_PATH.read_text(encoding="utf-8"))
        df = analyze_results.flatten_responses(results)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            analyze_results.analyze_concept_test(results, df, output_dir, report_only=True)

            persona_comparison_path = output_dir / "persona_comparison.csv"
            self.assertTrue(persona_comparison_path.exists())
            self.assertFalse((output_dir / "cross_tabs.csv").exists())
            self.assertFalse((output_dir / "cross_tabs_pct.csv").exists())

            with persona_comparison_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))

            self.assertEqual(len(rows) - 1, len(results))


if __name__ == "__main__":
    unittest.main()

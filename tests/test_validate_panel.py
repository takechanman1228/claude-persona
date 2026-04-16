import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


def load_module(module_name: str, relative_path: str):
    script_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


vp = load_module("validate_panel", "scripts/validate_panel.py")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_persona(
    name,
    age,
    gender,
    occupation_title,
    residence,
    segment,
    segment_id,
    big_five=None,
):
    if big_five is None:
        big_five = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }
    return {
        "persona": {
            "name": name,
            "age": age,
            "nationality": "American",
            "occupation": {
                "title": occupation_title,
                "organization": "TestCo",
                "description": "Test description.",
            },
            "gender": gender,
            "residence": residence,
            "education": "Test education",
            "long_term_goals": ["goal1"],
            "style": "Test style sentence one. Test style sentence two. Test style sentence three.",
            "personality": {
                "traits": ["trait1", "trait2"],
                "big_five": big_five,
            },
            "preferences": {
                "interests": ["interest1"],
                "likes": ["like1"],
                "dislikes": ["dislike1"],
            },
            "beliefs": ["belief1"],
            "skills": ["skill1"],
            "behaviors": {
                "general": ["behavior1"],
                "routines": {
                    "morning": ["wake up"],
                    "workday": ["work"],
                    "evening": ["rest"],
                    "weekend": ["relax"],
                },
            },
            "health": {"physical": "Healthy", "mental": "Stable"},
            "relationships": [
                {"name": "Friend", "relation": "friend", "description": "A friend"}
            ],
        },
        "segment": segment,
        "segment_id": segment_id,
    }


def _make_manifest(segments=None, persona_files=None, mode="segment-driven", total=None):
    m = {
        "survey_id": "test-panel",
        "topic": "Test topic",
        "category": "Test Category",
        "market": "United States",
        "generation_mode": mode,
        "total_personas": total if total is not None else (len(persona_files) if persona_files else 0),
        "created": "2026-04-14",
        "persona_files": persona_files or [],
    }
    if segments:
        m["segments"] = segments
    return m


def _write_panel(tmpdir, manifest, personas):
    """Write manifest and persona files to a temp directory. Returns Path."""
    panel_dir = Path(tmpdir)
    with open(panel_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    for p in personas:
        name = p["persona"]["name"].replace(" ", "_")
        filename = f"{name}.json"
        with open(panel_dir / filename, "w", encoding="utf-8") as f:
            json.dump(p, f)
    return panel_dir


# ---------------------------------------------------------------------------
# A clean 6-persona panel for reuse
# ---------------------------------------------------------------------------


def _clean_panel():
    """Return (manifest, personas) for a clean 6-persona panel, 2 segments x 3."""
    personas = [
        _make_persona("Alice Johnson", 28, "Female", "Nurse", "Austin, TX", "Runners", 1,
                       {"openness": 0.9, "conscientiousness": 0.3, "extraversion": 0.8, "agreeableness": 0.2, "neuroticism": 0.1}),
        _make_persona("Bob Martinez", 35, "Male", "Teacher", "Denver, CO", "Runners", 1,
                       {"openness": 0.2, "conscientiousness": 0.9, "extraversion": 0.1, "agreeableness": 0.8, "neuroticism": 0.7}),
        _make_persona("Chen Wei", 42, "Male", "Architect", "Portland, OR", "Runners", 1,
                       {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.9, "agreeableness": 0.1, "neuroticism": 0.3}),
        _make_persona("Diana Okafor", 31, "Female", "Accountant", "Atlanta, GA", "Joggers", 2,
                       {"openness": 0.1, "conscientiousness": 0.8, "extraversion": 0.4, "agreeableness": 0.9, "neuroticism": 0.2}),
        _make_persona("Erik Svensson", 50, "Male", "Chef", "Chicago, IL", "Joggers", 2,
                       {"openness": 0.7, "conscientiousness": 0.2, "extraversion": 0.3, "agreeableness": 0.4, "neuroticism": 0.9}),
        _make_persona("Fatima Al-Rashid", 25, "Female", "Barista", "Seattle, WA", "Joggers", 2,
                       {"openness": 0.4, "conscientiousness": 0.7, "extraversion": 0.6, "agreeableness": 0.5, "neuroticism": 0.5}),
    ]
    files = [f"{p['persona']['name'].replace(' ', '_')}.json" for p in personas]
    manifest = _make_manifest(
        segments=[
            {"name": "Runners", "segment_id": 1, "count": 3, "description": "Serious runners"},
            {"name": "Joggers", "segment_id": 2, "count": 3, "description": "Casual joggers"},
        ],
        persona_files=files,
        total=6,
    )
    return manifest, personas


# ===========================================================================
# Test Classes
# ===========================================================================


class TotalCountTests(unittest.TestCase):
    def test_passes_when_counts_match(self):
        manifest, personas = _clean_panel()
        result = vp.check_total_count(manifest, personas, requested_count=6)
        self.assertTrue(result["passed"])
        self.assertEqual(result["severity"], "fail")

    def test_fails_when_actual_exceeds_manifest(self):
        manifest, personas = _clean_panel()
        manifest["total_personas"] = 5  # wrong
        result = vp.check_total_count(manifest, personas, requested_count=6)
        self.assertFalse(result["passed"])
        self.assertIn("manifest says 5 but 6 loaded", result["details"]["issues"])

    def test_passes_without_requested_count(self):
        manifest, personas = _clean_panel()
        result = vp.check_total_count(manifest, personas)
        self.assertTrue(result["passed"])


class SegmentBalanceTests(unittest.TestCase):
    def test_passes_when_balanced(self):
        manifest, personas = _clean_panel()
        result = vp.check_segment_balance(manifest, personas)
        self.assertTrue(result["passed"])

    def test_fails_when_imbalanced(self):
        manifest, personas = _clean_panel()
        # Change one persona's segment to create imbalance
        personas[0]["segment"] = "Joggers"
        result = vp.check_segment_balance(manifest, personas)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["details"]["mismatches"]), 2)

    def test_topic_only_skips(self):
        manifest, personas = _clean_panel()
        manifest["generation_mode"] = "topic-only"
        del manifest["segments"]
        result = vp.check_segment_balance(manifest, personas)
        self.assertTrue(result["passed"])


class SegmentMetadataTests(unittest.TestCase):
    def test_passes_when_all_have_descriptions(self):
        manifest, personas = _clean_panel()
        result = vp.check_segment_metadata(manifest, personas)
        self.assertTrue(result["passed"])

    def test_fails_when_description_missing(self):
        manifest, personas = _clean_panel()
        del manifest["segments"][0]["description"]
        result = vp.check_segment_metadata(manifest, personas)
        self.assertFalse(result["passed"])
        self.assertIn("Runners", result["details"]["missing_descriptions"])


class NameUniquenessTests(unittest.TestCase):
    def test_passes_with_unique_names(self):
        manifest, personas = _clean_panel()
        result = vp.check_name_uniqueness(manifest, personas)
        self.assertTrue(result["passed"])
        self.assertEqual(result["severity"], "fail")

    def test_fails_with_duplicate_full_names(self):
        manifest, personas = _clean_panel()
        personas[1]["persona"]["name"] = "Alice Johnson"
        result = vp.check_name_uniqueness(manifest, personas)
        self.assertFalse(result["passed"])
        self.assertIn("Alice Johnson", result["details"]["duplicates"])

    def test_severity_is_fail(self):
        manifest, personas = _clean_panel()
        result = vp.check_name_uniqueness(manifest, personas)
        self.assertEqual(result["severity"], "fail")


class SurnameDiversityTests(unittest.TestCase):
    def test_passes_with_unique_surnames(self):
        manifest, personas = _clean_panel()
        result = vp.check_surname_diversity(manifest, personas)
        self.assertTrue(result["passed"])

    def test_warns_when_surname_appears_three_times(self):
        manifest, personas = _clean_panel()
        # Give 3 personas the same surname
        personas[0]["persona"]["name"] = "Alice Smith"
        personas[1]["persona"]["name"] = "Bob Smith"
        personas[2]["persona"]["name"] = "Chen Smith"
        result = vp.check_surname_diversity(manifest, personas)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")
        self.assertIn("Smith", result["details"]["over_represented"])

    def test_allows_two_same_surnames(self):
        manifest, personas = _clean_panel()
        personas[0]["persona"]["name"] = "Alice Kim"
        personas[1]["persona"]["name"] = "Bob Kim"
        result = vp.check_surname_diversity(manifest, personas)
        self.assertTrue(result["passed"])


class OccupationDiversityTests(unittest.TestCase):
    def test_passes_with_unique_occupations(self):
        manifest, personas = _clean_panel()
        result = vp.check_occupation_diversity(manifest, personas)
        self.assertTrue(result["passed"])

    def test_warns_with_duplicate_occupation(self):
        manifest, personas = _clean_panel()
        personas[1]["persona"]["occupation"]["title"] = "Nurse"  # Same as Alice
        result = vp.check_occupation_diversity(manifest, personas)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")

    def test_case_insensitive_comparison(self):
        manifest, personas = _clean_panel()
        personas[1]["persona"]["occupation"]["title"] = "nurse"
        result = vp.check_occupation_diversity(manifest, personas)
        self.assertFalse(result["passed"])


class GeoSpreadTests(unittest.TestCase):
    def test_passes_with_sufficient_spread(self):
        manifest, personas = _clean_panel()
        result = vp.check_geo_spread(manifest, personas)
        self.assertTrue(result["passed"])

    def test_warns_when_single_state(self):
        manifest, personas = _clean_panel()
        # Put all Runners in same state
        for p in personas:
            if p["segment"] == "Runners":
                p["persona"]["residence"] = "Dallas, TX"
        # Need 5+ personas in a segment for this check to trigger
        # Add 2 more to Runners
        extra1 = _make_persona("Greg Hall", 38, "Male", "Plumber", "Houston, TX", "Runners", 1)
        extra2 = _make_persona("Hana Park", 27, "Female", "Designer", "El Paso, TX", "Runners", 1)
        personas.extend([extra1, extra2])
        manifest["segments"][0]["count"] = 5
        manifest["total_personas"] = 8
        result = vp.check_geo_spread(manifest, personas)
        self.assertFalse(result["passed"])
        self.assertTrue(any("Runners" in w for w in result["details"]["warnings"]))


class AgeSpreadTests(unittest.TestCase):
    def test_passes_with_spread(self):
        manifest, personas = _clean_panel()
        result = vp.check_age_spread(manifest, personas)
        self.assertTrue(result["passed"])

    def test_warns_when_three_in_same_bracket(self):
        manifest, personas = _clean_panel()
        # Put 3 Runners in the same 5-year bracket (30-34)
        personas[0]["persona"]["age"] = 30
        personas[1]["persona"]["age"] = 32
        personas[2]["persona"]["age"] = 34
        result = vp.check_age_spread(manifest, personas)
        self.assertFalse(result["passed"])

    def test_bracket_boundaries(self):
        # 24 -> '20-24', 25 -> '25-29' — different brackets
        self.assertEqual(vp._age_bucket(24), "20-24")
        self.assertEqual(vp._age_bucket(25), "25-29")
        self.assertNotEqual(vp._age_bucket(24), vp._age_bucket(25))


class GenderDistributionTests(unittest.TestCase):
    def test_passes_with_balanced_gender(self):
        manifest, personas = _clean_panel()
        result = vp.check_gender_distribution(manifest, personas)
        self.assertTrue(result["passed"])

    def test_warns_when_minority_below_30_percent(self):
        # Build a segment with 5 personas: 4M, 1F = 20% minority
        personas = [
            _make_persona(f"Person {i}", 30 + i, "Male", f"Job{i}", f"City{i}, S{i}", "Seg", 1)
            for i in range(4)
        ]
        personas.append(
            _make_persona("Person 4", 40, "Female", "Job4", "City4, S4", "Seg", 1)
        )
        manifest = _make_manifest(
            segments=[{"name": "Seg", "segment_id": 1, "count": 5, "description": "Test"}],
            persona_files=[f"Person_{i}.json" for i in range(5)],
            total=5,
        )
        result = vp.check_gender_distribution(manifest, personas)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")


class BigFiveSimilarityTests(unittest.TestCase):
    def test_cosine_similarity_calculation(self):
        a = [1.0, 0.0, 0.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0, 0.0, 0.0]
        self.assertAlmostEqual(vp._cosine_similarity(a, b), 0.0)

    def test_identical_vectors_have_similarity_one(self):
        a = [0.5, 0.6, 0.7, 0.4, 0.3]
        self.assertAlmostEqual(vp._cosine_similarity(a, a), 1.0)

    def test_passes_below_threshold(self):
        manifest, personas = _clean_panel()
        result = vp.check_big_five_similarity(manifest, personas)
        self.assertTrue(result["passed"])

    def test_warns_above_threshold(self):
        manifest, personas = _clean_panel()
        # Make two personas have identical Big Five (cosine sim = 1.0, well above 0.98)
        same_bf = {"openness": 0.7, "conscientiousness": 0.6, "extraversion": 0.5,
                   "agreeableness": 0.4, "neuroticism": 0.3}
        personas[0]["persona"]["personality"]["big_five"] = same_bf.copy()
        personas[1]["persona"]["personality"]["big_five"] = same_bf.copy()
        result = vp.check_big_five_similarity(manifest, personas)
        self.assertFalse(result["passed"])
        self.assertEqual(result["severity"], "warning")
        self.assertGreater(len(result["details"]["high_similarity_pairs"]), 0)


class OverallPassTests(unittest.TestCase):
    def test_clean_panel_passes(self):
        manifest, personas = _clean_panel()
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_panel(tmpdir, manifest, personas)
            result = vp.validate_panel(Path(tmpdir), requested_count=6)
            self.assertTrue(result["overall_pass"])
            self.assertEqual(result["hard_fails"], 0)

    def test_warning_only_still_passes(self):
        manifest, personas = _clean_panel()
        # Create an occupation duplicate (warning, not fail)
        personas[1]["persona"]["occupation"]["title"] = "Nurse"
        files = [f"{p['persona']['name'].replace(' ', '_')}.json" for p in personas]
        manifest["persona_files"] = files
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_panel(tmpdir, manifest, personas)
            result = vp.validate_panel(Path(tmpdir))
            self.assertTrue(result["overall_pass"])
            self.assertGreater(result["warnings"], 0)

    def test_hard_fail_fails_overall(self):
        manifest, personas = _clean_panel()
        manifest["total_personas"] = 999  # wrong count
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_panel(tmpdir, manifest, personas)
            result = vp.validate_panel(Path(tmpdir))
            self.assertFalse(result["overall_pass"])
            self.assertGreater(result["hard_fails"], 0)


class DemoPanelTests(unittest.TestCase):
    """Run validator against the demo/running-shoes panel."""

    def test_demo_panel_passes(self):
        demo_dir = Path(__file__).resolve().parents[1] / "demo" / "running-shoes" / "personas"
        if not demo_dir.exists():
            self.skipTest("Demo panel not found")
        result = vp.validate_panel(demo_dir)
        # Demo panel should have zero hard fails
        self.assertEqual(result["hard_fails"], 0, f"Hard fails: {result['checks']}")
        self.assertTrue(result["overall_pass"])


class HelperTests(unittest.TestCase):
    def test_extract_state(self):
        self.assertEqual(vp._extract_state("Austin, TX"), "TX")
        self.assertEqual(vp._extract_state("Portland, OR"), "OR")
        self.assertEqual(vp._extract_state("Crown Heights, Brooklyn, NY"), "NY")

    def test_age_bucket(self):
        self.assertEqual(vp._age_bucket(22), "20-24")
        self.assertEqual(vp._age_bucket(30), "30-34")
        self.assertEqual(vp._age_bucket(55), "55-59")
        self.assertEqual(vp._age_bucket(18), "15-19")

    def test_get_surname(self):
        self.assertEqual(vp._get_surname("Alice Johnson"), "Johnson")
        self.assertEqual(vp._get_surname("Ava Johansson Kirk"), "Kirk")
        self.assertEqual(vp._get_surname("Chen"), "Chen")


if __name__ == "__main__":
    unittest.main()

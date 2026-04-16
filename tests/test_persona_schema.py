import json
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
PANEL_DIR = SKILL_DIR / "demo" / "running-shoes" / "personas"
MANIFEST_PATH = PANEL_DIR / "manifest.json"
BIG_FIVE_KEYS = {
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
}


class DemoPersonaSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.persona_paths = [
            PANEL_DIR / filename
            for filename in cls.manifest["persona_files"]
        ]
        cls.personas = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in cls.persona_paths
        ]

    def test_manifest_matches_demo_fixture(self):
        self.assertEqual(self.manifest["generation_mode"], "topic-only")
        self.assertTrue(str(self.manifest["topic"]).strip())
        self.assertTrue(str(self.manifest["category"]).strip())
        self.assertEqual(self.manifest["total_personas"], 15)
        self.assertEqual(len(self.manifest["persona_files"]), 15)

        for path in self.persona_paths:
            self.assertTrue(path.exists(), msg=f"Missing persona file: {path.name}")

    def test_each_persona_has_required_fields_and_valid_big_five_ranges(self):
        required_persona_fields = [
            "name",
            "age",
            "occupation",
            "gender",
            "residence",
            "education",
            "style",
            "personality",
        ]

        for path, document in zip(self.persona_paths, self.personas):
            with self.subTest(persona=path.name):
                self.assertIn("persona", document)
                self.assertIn("segment", document)
                self.assertIn("segment_id", document)
                self.assertTrue(str(document["segment"]).strip())

                persona = document["persona"]
                for field in required_persona_fields:
                    self.assertIn(field, persona)

                self.assertTrue(str(persona["name"]).strip())
                self.assertIsInstance(persona["age"], int)
                self.assertGreater(persona["age"], 0)
                self.assertTrue(str(persona["gender"]).strip())
                self.assertTrue(str(persona["residence"]).strip())
                self.assertTrue(str(persona["education"]).strip())
                self.assertGreaterEqual(len(str(persona["style"]).strip()), 150)

                occupation = persona["occupation"]
                self.assertIsInstance(occupation, dict)
                self.assertTrue(str(occupation.get("title", "")).strip())

                personality = persona["personality"]
                self.assertIsInstance(personality, dict)
                self.assertIn("big_five", personality)
                self.assertEqual(set(personality["big_five"].keys()), BIG_FIVE_KEYS)
                for trait, value in personality["big_five"].items():
                    self.assertIsInstance(value, (int, float), msg=f"{trait} must be numeric")
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 1.0)

    def test_demo_persona_names_and_segments_are_unique(self):
        names = [persona["persona"]["name"] for persona in self.personas]
        segments = [persona["segment"] for persona in self.personas]

        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(segments), len(set(segments)))


if __name__ == "__main__":
    unittest.main()

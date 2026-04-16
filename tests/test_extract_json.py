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


llm_backends = load_module("llm_backends", "scripts/llm_backends.py")


class ExtractJsonFromTextTests(unittest.TestCase):
    def test_plain_json_object(self):
        result = llm_backends.extract_json_from_text('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_plain_json_array(self):
        result = llm_backends.extract_json_from_text('[1, 2, 3]')
        self.assertEqual(result, [1, 2, 3])

    def test_fenced_json_block(self):
        text = 'Here is the result:\n```json\n{"responses": {"a": 1}}\n```\nDone.'
        result = llm_backends.extract_json_from_text(text)
        self.assertEqual(result, {"responses": {"a": 1}})

    def test_fenced_block_without_language_tag(self):
        text = 'Output:\n```\n{"x": true}\n```'
        result = llm_backends.extract_json_from_text(text)
        self.assertEqual(result, {"x": True})

    def test_bare_object_in_surrounding_text(self):
        text = 'The answer is {"preferred_option": "B"} as shown above.'
        result = llm_backends.extract_json_from_text(text)
        self.assertEqual(result, {"preferred_option": "B"})

    def test_bare_array_in_surrounding_text(self):
        text = 'Results: ["alpha", "beta"] end.'
        result = llm_backends.extract_json_from_text(text)
        self.assertEqual(result, ["alpha", "beta"])

    def test_multiline_fenced_json(self):
        text = (
            "```json\n"
            "{\n"
            '  "responses": {\n'
            '    "preferred_option": "A",\n'
            '    "reasoning": "It fits my needs."\n'
            "  }\n"
            "}\n"
            "```"
        )
        result = llm_backends.extract_json_from_text(text)
        self.assertEqual(result["responses"]["preferred_option"], "A")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            llm_backends.extract_json_from_text("")
        self.assertIn("Empty response text", str(ctx.exception))

    def test_none_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            llm_backends.extract_json_from_text(None)
        self.assertIn("Empty response text", str(ctx.exception))

    def test_whitespace_only_raises_value_error(self):
        with self.assertRaises(ValueError):
            llm_backends.extract_json_from_text("   \n\t  ")

    def test_no_json_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            llm_backends.extract_json_from_text("This is just plain text with no JSON.")
        self.assertIn("Could not extract valid JSON", str(ctx.exception))

    def test_malformed_json_raises_value_error(self):
        with self.assertRaises(ValueError):
            llm_backends.extract_json_from_text('{"key": value_without_quotes}')

    def test_unicode_content_preserved(self):
        text = '{"name": "田中ゆき", "age": 28}'
        result = llm_backends.extract_json_from_text(text)
        self.assertEqual(result["name"], "田中ゆき")

    def test_nested_json_object(self):
        text = '{"outer": {"inner": [1, 2, {"deep": true}]}}'
        result = llm_backends.extract_json_from_text(text)
        self.assertEqual(result["outer"]["inner"][2]["deep"], True)


if __name__ == "__main__":
    unittest.main()

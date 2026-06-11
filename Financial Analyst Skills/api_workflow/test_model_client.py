from __future__ import annotations

import unittest

from api_workflow.model_client import parse_json_object


class ModelClientJsonRepairTests(unittest.TestCase):
    def test_parse_json_object_repairs_smart_quotes(self) -> None:
        raw = """{
  “company”: {
    “company_name”: “贵州茅台”
  }
}"""
        parsed = parse_json_object(raw)
        self.assertEqual(parsed["company"]["company_name"], "贵州茅台")

    def test_parse_json_object_removes_trailing_commas(self) -> None:
        raw = """{
  "company": {
    "company_name": "贵州茅台",
  },
}"""
        parsed = parse_json_object(raw)
        self.assertEqual(parsed["company"]["company_name"], "贵州茅台")


if __name__ == "__main__":
    unittest.main()

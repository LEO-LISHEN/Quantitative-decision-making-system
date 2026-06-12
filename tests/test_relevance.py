import sys
import unittest
from pathlib import Path


SKILLS_DIR = Path(__file__).resolve().parents[1] / "Financial Analyst Skills"
sys.path.insert(0, str(SKILLS_DIR))

from api_workflow.relevance import is_stock_analysis_related  # noqa: E402


class RelevanceTests(unittest.TestCase):
    def test_accepts_company_name_analysis_without_ticker(self):
        self.assertTrue(is_stock_analysis_related("帮我分析一下蓝思科技"))

    def test_rejects_unrelated_analysis_request(self):
        self.assertFalse(is_stock_analysis_related("帮我分析一下明天的天气"))

    def test_accepts_explicit_ticker(self):
        self.assertTrue(is_stock_analysis_related("分析 300433.SZ"))


if __name__ == "__main__":
    unittest.main()

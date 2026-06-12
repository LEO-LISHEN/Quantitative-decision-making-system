import sys
import unittest
from pathlib import Path


EVENT_DIR = Path(__file__).resolve().parents[1] / "Event Focus"
sys.path.insert(0, str(EVENT_DIR))

from service import build_overview, fallback_payload, normalize_cards, normalize_published_at, normalize_title


class EventFocusTests(unittest.TestCase):
    def test_normalize_cards_adds_decision_fields(self):
        cards = normalize_cards(
            [
                {
                    "title": "政策事件",
                    "priority": "高",
                    "category": "政策",
                    "impact_direction": "利多",
                    "affected_assets": ["券商", "沪深300"],
                    "horizon": "1-4周",
                    "confidence": 0.82,
                }
            ],
            6,
        )

        self.assertEqual(cards[0]["impact_direction"], "利多")
        self.assertEqual(cards[0]["affected_assets"], ["券商", "沪深300"])
        self.assertEqual(cards[0]["confidence"], 0.82)

    def test_overview_counts_priority_and_direction(self):
        cards = [
            {"priority": "高", "impact_direction": "利多", "category": "政策"},
            {"priority": "中", "impact_direction": "利空", "category": "风险"},
        ]

        overview = build_overview(cards)

        self.assertEqual(overview["high_priority_count"], 1)
        self.assertEqual(overview["bullish_count"], 1)
        self.assertEqual(overview["bearish_count"], 1)

    def test_fallback_payload_is_schema_compatible(self):
        payload = fallback_payload(
            "a_share",
            [{"title": "测试事件", "summary": "事件摘要", "source": "测试源"}],
            "offline",
        )

        self.assertEqual(payload["cards"][0]["impact_direction"], "中性")
        self.assertIn("overview", payload)

    def test_title_and_time_normalization(self):
        self.assertEqual(normalize_title("重大政策落地 - 某某财经"), "重大政策落地")
        self.assertTrue(normalize_published_at("Fri, 12 Jun 2026 08:00:00 GMT").startswith("2026-06-12T16:00"))


if __name__ == "__main__":
    unittest.main()

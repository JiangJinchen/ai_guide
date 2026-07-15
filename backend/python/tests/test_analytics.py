import unittest
from unittest.mock import MagicMock, patch


try:
    from app.api.analytics import analytics_comparison

    ANALYTICS_DEPENDENCIES_AVAILABLE = True
except ModuleNotFoundError:
    ANALYTICS_DEPENDENCIES_AVAILABLE = False


@unittest.skipUnless(ANALYTICS_DEPENDENCIES_AVAILABLE, "fastapi and sqlalchemy are required")
class AnalyticsComparisonTests(unittest.TestCase):
    @patch("app.api.analytics.analytics_overview")
    def test_compares_equal_previous_period_and_handles_zero_baseline(self, overview):
        overview.side_effect = [
            {
                "visitor_count": 12,
                "session_count": 0,
                "interaction_count": 8,
                "route_count": 2,
                "feedback_count": 1,
                "average_spend": 150.0,
                "satisfaction_rate": 80.0,
            },
            {
                "visitor_count": 8,
                "session_count": 0,
                "interaction_count": 4,
                "route_count": 1,
                "feedback_count": 0,
                "average_spend": 100.0,
                "satisfaction_rate": 0.0,
            },
        ]

        result = analytics_comparison(
            start_date="2026-07-10",
            end_date="2026-07-12",
            db=MagicMock(),
        )

        self.assertEqual(result["period"], {"start_date": "2026-07-10", "end_date": "2026-07-12"})
        self.assertEqual(result["comparison_period"], {"start_date": "2026-07-07", "end_date": "2026-07-09"})
        self.assertEqual(result["changes"]["visitor_count"]["delta"], 4.0)
        self.assertEqual(result["changes"]["visitor_count"]["rate"], 50.0)
        self.assertIsNone(result["changes"]["feedback_count"]["rate"])
        self.assertEqual(result["changes"]["session_count"]["rate"], 0.0)


if __name__ == "__main__":
    unittest.main()

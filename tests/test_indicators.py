from unittest import TestCase

from rsi_trendline_agent.indicators import compute_rsi


class ComputeRsiTests(TestCase):
    def test_returns_none_until_period_is_available(self):
        values = compute_rsi([1, 2, 3, 4, 5], period=4)

        self.assertEqual(values[:4], [None, None, None, None])
        self.assertEqual(values[4], 100.0)

    def test_rsi_stays_between_zero_and_one_hundred(self):
        closes = [44, 44.15, 43.9, 44.35, 44.8, 44.3, 44.1, 44.7, 45.2, 44.9, 45.4]

        values = [value for value in compute_rsi(closes, period=5) if value is not None]

        self.assertTrue(values)
        self.assertTrue(all(0 <= value <= 100 for value in values))

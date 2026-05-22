from unittest import TestCase

from rsi_trendline_agent.trendline import (
    RsiPoint,
    Trendline,
    analyze_touches,
    should_send_alert,
)


def point(index: int, value: float) -> RsiPoint:
    return RsiPoint(index=index, timestamp=f"2026-01-{index + 1:02d}", value=value)


class TrendlineTouchTests(TestCase):
    def test_alerts_on_second_resistance_touch_after_anchors(self):
        points = [
            point(0, 60),
            point(5, 60),
            point(6, 50),
            point(8, 59.2),
            point(9, 49),
            point(12, 59.5),
        ]
        trendline = Trendline(side="resistance", first=points[0], second=points[1])

        analysis = analyze_touches(
            points,
            trendline,
            touch_tolerance=1.0,
            breakout_tolerance=0.5,
            min_bars_between_touches=2,
            alert_on_touch_number=2,
        )

        self.assertEqual(analysis.touch_count, 2)
        self.assertTrue(should_send_alert(analysis, 2))
        self.assertEqual(analysis.latest_event.index, 12)

    def test_breakout_before_target_touch_blocks_alert(self):
        points = [
            point(0, 60),
            point(5, 60),
            point(6, 61.0),
            point(8, 59.6),
        ]
        trendline = Trendline(side="resistance", first=points[0], second=points[1])

        analysis = analyze_touches(
            points,
            trendline,
            touch_tolerance=1.0,
            breakout_tolerance=0.5,
            min_bars_between_touches=2,
            alert_on_touch_number=2,
        )

        self.assertTrue(analysis.broken_before_target)
        self.assertFalse(should_send_alert(analysis, 2))

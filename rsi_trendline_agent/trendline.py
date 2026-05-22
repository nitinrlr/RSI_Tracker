from __future__ import annotations

from dataclasses import dataclass

from .config import TrendlineConfig


@dataclass(frozen=True)
class RsiPoint:
    index: int
    timestamp: str
    value: float


@dataclass(frozen=True)
class Trendline:
    side: str
    first: RsiPoint
    second: RsiPoint

    @property
    def slope(self) -> float:
        span = self.second.index - self.first.index
        if span == 0:
            raise ValueError("Trendline anchors must have different indexes")
        return (self.second.value - self.first.value) / span

    def value_at(self, index: int) -> float:
        return self.first.value + (self.slope * (index - self.first.index))

    @property
    def key(self) -> str:
        return (
            f"{self.side}:"
            f"{self.first.index}:{self.first.timestamp}:{self.first.value:.4f}:"
            f"{self.second.index}:{self.second.timestamp}:{self.second.value:.4f}"
        )


@dataclass(frozen=True)
class TouchEvent:
    index: int
    timestamp: str
    rsi: float
    trendline_value: float
    broke_through: bool


@dataclass(frozen=True)
class TrendlineAnalysis:
    trendline: Trendline
    touch_events: tuple[TouchEvent, ...]
    broken_before_target: bool
    latest_event: TouchEvent | None
    target_event: TouchEvent | None
    latest_point_index: int

    @property
    def touch_count(self) -> int:
        return len(self.touch_events)


def build_trendline(points: list[RsiPoint], config: TrendlineConfig) -> Trendline:
    if config.side not in {"resistance", "support"}:
        raise ValueError("trendline.side must be either 'resistance' or 'support'")
    if config.mode == "manual":
        return _manual_trendline(points, config)
    if config.mode == "auto":
        return _auto_trendline(points, config)
    raise ValueError("trendline.mode must be either 'auto' or 'manual'")


def analyze_touches(
    points: list[RsiPoint],
    trendline: Trendline,
    *,
    touch_tolerance: float,
    breakout_tolerance: float,
    min_bars_between_touches: int,
    alert_on_touch_number: int,
) -> TrendlineAnalysis:
    if touch_tolerance < 0:
        raise ValueError("touch_tolerance must be non-negative")
    if breakout_tolerance < 0:
        raise ValueError("breakout_tolerance must be non-negative")
    if min_bars_between_touches < 1:
        raise ValueError("min_bars_between_touches must be at least 1")
    if alert_on_touch_number < 1:
        raise ValueError("alert_on_touch_number must be at least 1")

    events: list[TouchEvent] = []
    latest_event: TouchEvent | None = None
    target_event: TouchEvent | None = None
    broken_before_target = False
    in_touch_zone = False
    last_event_index: int | None = None
    latest_point_index = points[-1].index if points else -1

    for point in points:
        if point.index <= trendline.second.index:
            continue

        line_value = trendline.value_at(point.index)
        reached = _reaches_line(point.value, line_value, trendline.side, touch_tolerance)
        broke = _breaks_line(point.value, line_value, trendline.side, breakout_tolerance)
        enough_space = (
            last_event_index is None
            or point.index - last_event_index >= min_bars_between_touches
        )

        if reached and not in_touch_zone and enough_space:
            event = TouchEvent(
                index=point.index,
                timestamp=point.timestamp,
                rsi=point.value,
                trendline_value=line_value,
                broke_through=broke,
            )
            events.append(event)
            latest_event = event
            last_event_index = point.index

            if len(events) == alert_on_touch_number:
                target_event = event

        if broke and len(events) < alert_on_touch_number:
            broken_before_target = True
            break

        in_touch_zone = reached

    return TrendlineAnalysis(
        trendline=trendline,
        touch_events=tuple(events),
        broken_before_target=broken_before_target,
        latest_event=latest_event,
        target_event=target_event,
        latest_point_index=latest_point_index,
    )


def should_send_alert(analysis: TrendlineAnalysis, alert_on_touch_number: int) -> bool:
    return (
        not analysis.broken_before_target
        and analysis.target_event is not None
        and len(analysis.touch_events) >= alert_on_touch_number
        and analysis.target_event.index == analysis.latest_point_index
    )


def _manual_trendline(points: list[RsiPoint], config: TrendlineConfig) -> Trendline:
    if not config.manual_anchors:
        raise ValueError("Manual trendline mode requires trendline.manual_anchors")

    anchors: list[RsiPoint] = []
    for anchor in config.manual_anchors:
        point = next((item for item in points if item.timestamp.startswith(anchor.date)), None)
        if point is None:
            raise ValueError(f"No RSI point found for manual anchor date {anchor.date}")
        if anchor.rsi is not None:
            point = RsiPoint(index=point.index, timestamp=point.timestamp, value=float(anchor.rsi))
        anchors.append(point)

    anchors.sort(key=lambda item: item.index)
    return Trendline(side=config.side, first=anchors[0], second=anchors[1])


def _auto_trendline(points: list[RsiPoint], config: TrendlineConfig) -> Trendline:
    lookback = config.pivot_lookback
    if lookback < 1:
        raise ValueError("trendline.pivot_lookback must be at least 1")

    pivots: list[RsiPoint] = []
    for index in range(lookback, len(points) - lookback):
        window = points[index - lookback : index + lookback + 1]
        current = points[index]
        neighbors = [item.value for item in window if item.index != current.index]
        if config.side == "resistance" and current.value > max(neighbors):
            pivots.append(current)
        elif config.side == "support" and current.value < min(neighbors):
            pivots.append(current)

    if len(pivots) < 2:
        raise ValueError(
            f"Could not find two RSI pivot {'highs' if config.side == 'resistance' else 'lows'}"
        )

    first, second = pivots[-2], pivots[-1]
    return Trendline(side=config.side, first=first, second=second)


def _reaches_line(rsi: float, line_value: float, side: str, tolerance: float) -> bool:
    if side == "resistance":
        return rsi >= line_value - tolerance
    return rsi <= line_value + tolerance


def _breaks_line(rsi: float, line_value: float, side: str, tolerance: float) -> bool:
    if side == "resistance":
        return rsi > line_value + tolerance
    return rsi < line_value - tolerance

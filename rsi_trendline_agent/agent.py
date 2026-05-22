from __future__ import annotations

from dataclasses import dataclass

from .config import AgentConfig, EmailConfig
from .data import PriceBar, YahooChartClient
from .emailer import send_email
from .indicators import compute_rsi
from .state import AlertState
from .trendline import (
    RsiPoint,
    TrendlineAnalysis,
    analyze_touches,
    build_trendline,
    should_send_alert,
)


@dataclass(frozen=True)
class AgentRunResult:
    symbol: str
    latest_timestamp: str
    latest_rsi: float
    trendline_key: str
    touch_count: int
    alert_sent: bool
    message: str


class RsiTrendlineAgent:
    def __init__(
        self,
        config: AgentConfig,
        *,
        data_client: YahooChartClient | None = None,
        email_config: EmailConfig | None = None,
        dry_run: bool = False,
    ) -> None:
        self.config = config
        self.data_client = data_client or YahooChartClient()
        self.email_config = email_config
        self.dry_run = dry_run

    def run_once(self) -> AgentRunResult:
        bars = self.data_client.fetch(
            self.config.symbol,
            range_=self.config.range,
            interval=self.config.interval,
        )
        points = _rsi_points(bars, self.config.rsi_period)
        if len(points) < self.config.rsi_period:
            raise RuntimeError("Not enough RSI points to analyze")

        trendline = build_trendline(points, self.config.trendline)
        analysis = analyze_touches(
            points,
            trendline,
            touch_tolerance=self.config.touch_tolerance,
            breakout_tolerance=self.config.breakout_tolerance,
            min_bars_between_touches=self.config.min_bars_between_touches,
            alert_on_touch_number=self.config.alert_on_touch_number,
        )

        latest = points[-1]
        state_key = f"{self.config.symbol}:{self.config.interval}:{trendline.key}"
        state = AlertState.load(self.config.state_file)
        alert_sent = False
        message = _status_message(self.config.symbol, latest, analysis.touch_count)

        if should_send_alert(analysis, self.config.alert_on_touch_number):
            event = analysis.target_event
            if event is None:
                raise RuntimeError("Expected target touch event")

            if state.already_alerted(state_key, event.index):
                message = "Alert condition is still active, but this event was already emailed."
            else:
                subject, body = _email_content(self.config, analysis)
                if self.dry_run:
                    print("DRY RUN EMAIL")
                    print("Subject:", subject)
                    print(body)
                else:
                    if self.email_config is None:
                        raise ValueError("Email settings are required unless --dry-run is used")
                    send_email(self.email_config, subject, body)

                state.mark_alerted(
                    state_key,
                    event.index,
                    {
                        "symbol": self.config.symbol,
                        "timestamp": event.timestamp,
                        "touch_count": analysis.touch_count,
                        "rsi": round(event.rsi, 4),
                        "trendline_value": round(event.trendline_value, 4),
                    },
                )
                state.save(self.config.state_file)
                alert_sent = True
                message = (
                    f"Trendline reach #{self.config.alert_on_touch_number} "
                    "detected; email alert sent."
                )

        return AgentRunResult(
            symbol=self.config.symbol,
            latest_timestamp=latest.timestamp,
            latest_rsi=latest.value,
            trendline_key=trendline.key,
            touch_count=analysis.touch_count,
            alert_sent=alert_sent,
            message=message,
        )


def _rsi_points(bars: list[PriceBar], period: int) -> list[RsiPoint]:
    closes = [bar.close for bar in bars]
    values = compute_rsi(closes, period)
    return [
        RsiPoint(index=index, timestamp=bar.timestamp, value=value)
        for index, (bar, value) in enumerate(zip(bars, values))
        if value is not None
    ]


def _status_message(symbol: str, latest: RsiPoint, touch_count: int) -> str:
    return (
        f"{symbol} latest RSI is {latest.value:.2f} at {latest.timestamp}; "
        f"current trendline touch count is {touch_count}."
    )


def _email_content(config: AgentConfig, analysis: TrendlineAnalysis) -> tuple[str, str]:
    event = analysis.target_event
    if event is None:
        raise RuntimeError("Cannot build email without a touch event")

    direction = "above" if event.broke_through else "at"
    subject = (
        f"{config.symbol} RSI trendline alert: "
        f"touch {analysis.touch_count} on {event.timestamp}"
    )
    body = "\n".join(
        [
            f"{config.symbol} RSI reached its {config.trendline.side} trendline for touch #{analysis.touch_count}.",
            "",
            f"Timestamp: {event.timestamp}",
            f"RSI: {event.rsi:.2f}",
            f"Trendline value: {event.trendline_value:.2f}",
            f"Status: RSI closed {direction} the configured trendline threshold.",
            "",
            "Trendline anchors:",
            f"- {analysis.trendline.first.timestamp}: RSI {analysis.trendline.first.value:.2f}",
            f"- {analysis.trendline.second.timestamp}: RSI {analysis.trendline.second.value:.2f}",
        ]
    )
    return subject, body

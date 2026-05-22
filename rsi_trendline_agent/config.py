from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ManualAnchor:
    date: str
    rsi: float | None = None


@dataclass(frozen=True)
class TrendlineConfig:
    mode: str = "auto"
    side: str = "resistance"
    pivot_lookback: int = 3
    manual_anchors: tuple[ManualAnchor, ManualAnchor] | None = None


@dataclass(frozen=True)
class AgentConfig:
    symbol: str = "AAPL"
    range: str = "1y"
    interval: str = "1d"
    rsi_period: int = 14
    trendline: TrendlineConfig = field(default_factory=TrendlineConfig)
    touch_tolerance: float = 1.5
    breakout_tolerance: float = 0.5
    min_bars_between_touches: int = 3
    alert_on_touch_number: int = 2
    state_file: str = "state/alerts.json"
    poll_seconds: int = 3600


@dataclass(frozen=True)
class EmailConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    sender: str
    recipients: tuple[str, ...]
    use_tls: bool = True


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_agent_config(path: str | Path | None) -> AgentConfig:
    if path is None:
        return AgentConfig()

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return parse_agent_config(raw)


def parse_agent_config(raw: dict[str, Any]) -> AgentConfig:
    trendline_raw = raw.get("trendline", {})

    trendline = TrendlineConfig(
        mode=str(trendline_raw.get("mode", "auto")).lower(),
        side=str(trendline_raw.get("side", "resistance")).lower(),
        pivot_lookback=int(trendline_raw.get("pivot_lookback", 3)),
        manual_anchors=_parse_manual_anchors(trendline_raw.get("manual_anchors")),
    )

    return AgentConfig(
        symbol=str(raw.get("symbol", "AAPL")).upper(),
        range=str(raw.get("range", "1y")),
        interval=str(raw.get("interval", "1d")),
        rsi_period=int(raw.get("rsi_period", 14)),
        trendline=trendline,
        touch_tolerance=float(raw.get("touch_tolerance", 1.5)),
        breakout_tolerance=float(raw.get("breakout_tolerance", 0.5)),
        min_bars_between_touches=int(raw.get("min_bars_between_touches", 3)),
        alert_on_touch_number=int(raw.get("alert_on_touch_number", 2)),
        state_file=str(raw.get("state_file", "state/alerts.json")),
        poll_seconds=int(raw.get("poll_seconds", 3600)),
    )


def _parse_manual_anchors(raw: Any) -> tuple[ManualAnchor, ManualAnchor] | None:
    if not raw:
        return None
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError("trendline.manual_anchors must contain exactly two anchors")

    anchors: list[ManualAnchor] = []
    for item in raw:
        if not isinstance(item, dict) or "date" not in item:
            raise ValueError("Each manual anchor must include a date")
        rsi = item.get("rsi")
        anchors.append(
            ManualAnchor(
                date=str(item["date"]),
                rsi=None if rsi is None else float(rsi),
            )
        )

    return anchors[0], anchors[1]


def load_email_config() -> EmailConfig:
    host = os.environ.get("SMTP_HOST")
    sender = os.environ.get("ALERT_EMAIL_FROM") or os.environ.get("SMTP_USERNAME")
    recipients_raw = os.environ.get("ALERT_EMAIL_TO")

    missing = [
        name
        for name, value in {
            "SMTP_HOST": host,
            "ALERT_EMAIL_FROM or SMTP_USERNAME": sender,
            "ALERT_EMAIL_TO": recipients_raw,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError("Missing email settings: " + ", ".join(missing))

    recipients = tuple(
        item.strip() for item in recipients_raw.replace(";", ",").split(",") if item.strip()
    )
    if not recipients:
        raise ValueError("ALERT_EMAIL_TO must contain at least one recipient")

    return EmailConfig(
        host=host,
        port=int(os.environ.get("SMTP_PORT", "587")),
        username=os.environ.get("SMTP_USERNAME"),
        password=os.environ.get("SMTP_PASSWORD"),
        sender=sender,
        recipients=recipients,
        use_tls=os.environ.get("SMTP_USE_TLS", "true").lower() not in {"0", "false", "no"},
    )

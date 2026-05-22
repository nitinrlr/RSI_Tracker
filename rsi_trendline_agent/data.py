from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PriceBar:
    timestamp: str
    close: float


class YahooChartClient:
    """Fetches OHLC data from Yahoo's chart endpoint without third-party packages."""

    def fetch(self, symbol: str, range_: str = "1y", interval: str = "1d") -> list[PriceBar]:
        encoded_symbol = urllib.parse.quote(symbol.upper(), safe="")
        params = urllib.parse.urlencode({"range": range_, "interval": interval})
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_symbol}?{params}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "rsi-trendline-alert-agent/0.1",
            },
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        chart = payload.get("chart", {})
        if chart.get("error"):
            raise RuntimeError(f"Yahoo chart error for {symbol}: {chart['error']}")

        results = chart.get("result") or []
        if not results:
            raise RuntimeError(f"No price data returned for {symbol}")

        result = results[0]
        timestamps = result.get("timestamp") or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []

        bars: list[PriceBar] = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            bars.append(
                PriceBar(
                    timestamp=_format_timestamp(int(ts), interval),
                    close=float(close),
                )
            )

        if not bars:
            raise RuntimeError(f"No usable close prices returned for {symbol}")
        return bars


def _format_timestamp(ts: int, interval: str) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    if interval.endswith("d") or interval.endswith("wk") or interval.endswith("mo"):
        return dt.date().isoformat()
    return dt.isoformat()

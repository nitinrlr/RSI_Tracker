# RSI Trendline Email Alert Agent

This is a small Python agent that watches a chosen stock, computes RSI, tracks
RSI trendline touches, and emails you when the second post-anchor touch happens.

The agent is deterministic rather than LLM-based. That is intentional for a
market alert: the fetch, RSI, trendline, touch count, and email behavior are all
auditable.

## How the Alert Works

1. Fetch recent close prices for `symbol`.
2. Compute Wilder RSI with `rsi_period`.
3. Build an RSI trendline:
   - `auto`: use the latest two RSI pivot highs for resistance or pivot lows for support.
   - `manual`: use two configured dates, optionally with explicit RSI values.
4. Treat those two pivot anchors as PA1 and PA2. They define the line but are not counted as touches.
5. Count each later entry into the trendline zone as one touch.
6. Send an email when touch 2 is detected by default.

Consecutive bars near the trendline count as one touch. A breakout before the
target touch invalidates the current trendline. If the target touch is also a
breakout, the alert still sends because RSI reached the line at the configured
alert point.

## Setup

Use the bundled Python shown by Codex or any local Python 3.11+ install.

```powershell
Copy-Item config.example.json config.json
Copy-Item .env.example .env
```

Edit `config.json` for the stock and trendline settings. Edit `.env` with SMTP
credentials. For Gmail, use an app password rather than your account password.

## Recommended: Run Automatically on Windows

For daily RSI checks, use Windows Task Scheduler. This is more reliable than
leaving VS Code open all day.

First test the agent without sending email:

```powershell
.\run-agent.ps1 -DryRun
```

If Windows says running scripts is disabled, use the `.cmd` wrapper instead:

```powershell
.\run-agent.cmd -DryRun
```

Then edit `.env` with real SMTP settings and test a real alert-capable run:

```powershell
.\run-agent.ps1
```

Or, if PowerShell scripts are blocked:

```powershell
.\run-agent.cmd
```

Install a daily scheduled task after market close:

```powershell
.\install-windows-task.ps1
```

Or, if PowerShell scripts are blocked:

```powershell
.\install-windows-task.cmd
```

By default, the task runs every day at `4:30PM`. To choose another time:

```powershell
.\install-windows-task.ps1 -At "5:00PM"
```

For intraday monitoring while your PC is awake, you can keep a loop running:

```powershell
.\run-agent.ps1 -Mode loop
```

## Run Once

```powershell
& 'C:\Users\nitin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m rsi_trendline_agent --config config.json --once --dry-run
```

Remove `--dry-run` after `.env` is configured:

```powershell
& 'C:\Users\nitin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m rsi_trendline_agent --config config.json --once
```

## Run Continuously

```powershell
& 'C:\Users\nitin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m rsi_trendline_agent --config config.json --loop
```

`poll_seconds` controls how often it checks. For daily RSI, running once per day
through Windows Task Scheduler is usually cleaner than a long-running loop.

## Manual Trendline Example

Use this when you want the line anchored on exact dates from your chart:

```json
{
  "trendline": {
    "mode": "manual",
    "side": "resistance",
    "manual_anchors": [
      { "date": "2026-02-03" },
      { "date": "2026-04-10" }
    ]
  }
}
```

If your chart uses a hand-drawn RSI value that differs from the computed RSI,
include it explicitly:

```json
{
  "manual_anchors": [
    { "date": "2026-02-03", "rsi": 68.4 },
    { "date": "2026-04-10", "rsi": 62.1 }
  ]
}
```

## Configuration

- `symbol`: ticker to watch, for example `AAPL`, `MSFT`, `SPY`.
- `range`: Yahoo chart range, for example `6mo`, `1y`, `2y`.
- `interval`: Yahoo chart interval, for example `1d`, `1h`, `15m`.
- `trendline.side`: `resistance` for upside attempts, `support` for downside attempts.
- `touch_tolerance`: RSI points away from the line that count as a reach.
- `breakout_tolerance`: RSI points beyond the line that count as a break.
- `min_bars_between_touches`: debounce window to prevent one touch from being counted repeatedly.
- `alert_on_touch_number`: touch count that triggers an alert. The default is `2`, meaning PA1 and PA2 define the line, touch 1 is observed, and touch 2 triggers the email.
- `state_file`: local JSON file used to avoid duplicate email alerts.

## Tests

```powershell
& 'C:\Users\nitin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests
```

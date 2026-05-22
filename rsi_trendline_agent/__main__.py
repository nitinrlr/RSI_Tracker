from __future__ import annotations

import argparse
import time
from dataclasses import replace

from .agent import RsiTrendlineAgent
from .config import load_agent_config, load_dotenv, load_email_config


def main() -> None:
    parser = argparse.ArgumentParser(description="RSI trendline email alert agent")
    parser.add_argument("--config", default="config.json", help="Path to JSON config file")
    parser.add_argument("--env-file", default=".env", help="Path to environment file")
    parser.add_argument("--symbol", help="Override the symbol from the config file")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--dry-run", action="store_true", help="Print the email instead of sending it")
    args = parser.parse_args()

    load_dotenv(args.env_file)
    config = load_agent_config(args.config)
    if args.symbol:
        config = replace(config, symbol=args.symbol.upper())

    if args.loop and args.once:
        raise SystemExit("Use either --once or --loop, not both")

    email_config = None if args.dry_run else load_email_config()
    agent = RsiTrendlineAgent(config, email_config=email_config, dry_run=args.dry_run)
    run_once = args.once or not args.loop

    while True:
        result = agent.run_once()
        print(
            f"{result.symbol} {result.latest_timestamp} RSI={result.latest_rsi:.2f} "
            f"touches={result.touch_count} alert_sent={result.alert_sent}"
        )
        print(result.message)

        if run_once:
            return
        time.sleep(config.poll_seconds)


if __name__ == "__main__":
    main()

"""Command-line entry point."""

from __future__ import annotations

import argparse
import logging

from issue_scout.config import Config, ConfigurationError
from issue_scout.github_api import GitHubApi
from issue_scout.slack import SlackNotifier
from issue_scout.state import StateStore
from issue_scout.watcher import Watcher


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify Slack when new GitHub issues open.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="check each repository once, then exit",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        config = Config.load()
    except ConfigurationError as exc:
        logging.error("Configuration error: %s", exc)
        return 2

    store = StateStore(config.database_path)
    watcher = Watcher(
        repos=config.repos,
        poll_interval_seconds=config.poll_interval_seconds,
        github=GitHubApi(config.github_token),
        slack=SlackNotifier(config.slack_webhook_url),
        state=store,
    )
    try:
        if args.once:
            watcher.run_once()
        else:
            watcher.run_forever()
    except KeyboardInterrupt:
        logging.info("Stopping Issue Scout.")
    finally:
        store.close()
    return 0

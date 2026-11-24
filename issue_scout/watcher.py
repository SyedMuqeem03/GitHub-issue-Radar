"""Polling loop that finds new issues and sends alerts."""

from __future__ import annotations

import logging
import time
from typing import Any

from issue_scout.github_api import GitHubApi, PER_PAGE
from issue_scout.slack import SlackNotifier
from issue_scout.state import StateStore


LOGGER = logging.getLogger(__name__)


class Watcher:
    def __init__(
        self,
        repos: tuple[str, ...],
        poll_interval_seconds: int,
        github: GitHubApi,
        slack: SlackNotifier,
        state: StateStore,
    ) -> None:
        self.repos = repos
        self.poll_interval_seconds = poll_interval_seconds
        self.github = github
        self.slack = slack
        self.state = state

    def run_once(self) -> None:
        for repo in self.repos:
            try:
                self._poll_repo(repo)
            except Exception:
                LOGGER.exception("Could not check %s; it will be retried next time.", repo)

    def run_forever(self) -> None:
        LOGGER.info(
            "Watching %d repositories every %d seconds. Press Ctrl+C to stop.",
            len(self.repos),
            self.poll_interval_seconds,
        )
        while True:
            started = time.monotonic()
            self.run_once()
            elapsed = time.monotonic() - started
            time.sleep(max(0, self.poll_interval_seconds - elapsed))

    def _poll_repo(self, repo: str) -> None:
        cursor = self.state.get_cursor(repo)
        if cursor is None:
            first_page = self.github.list_issues(repo, page=1)
            latest_number = max((self._number(issue) for issue in first_page), default=0)
            self.state.initialize_repo(repo, latest_number)
            LOGGER.info("Established baseline for %s at issue number %d.", repo, latest_number)
            return

        highest_number = cursor
        page = 1
        while True:
            issues = self.github.list_issues(repo, page=page)
            if not issues:
                break

            page_numbers = [self._number(issue) for issue in issues]
            highest_number = max(highest_number, max(page_numbers))

            for issue in issues:
                issue_number = self._number(issue)
                if issue_number <= cursor or self._is_pull_request(issue):
                    continue
                if self.state.was_notified(repo, issue_number):
                    continue

                self.slack.notify_issue(repo, issue)
                self.state.mark_notified(repo, issue_number)
                LOGGER.info("Sent alert for %s issue #%d.", repo, issue_number)

            if max(page_numbers) <= cursor or len(issues) < PER_PAGE:
                break
            page += 1

        if highest_number > cursor:
            self.state.update_cursor(repo, highest_number)

    @staticmethod
    def _number(issue: dict[str, Any]) -> int:
        return int(issue["number"])

    @staticmethod
    def _is_pull_request(issue: dict[str, Any]) -> bool:
        return "pull_request" in issue

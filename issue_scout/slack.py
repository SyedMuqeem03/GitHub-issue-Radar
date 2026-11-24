"""Slack incoming-webhook notifications."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SlackError(RuntimeError):
    """Raised when Slack does not accept a notification."""


def _safe_mrkdwn(value: str) -> str:
    """Escape Slack's special angle-bracket syntax, including mention syntax."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SlackNotifier:
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def notify_issue(self, repo: str, issue: dict[str, Any]) -> None:
        number = int(issue["number"])
        title = str(issue.get("title") or "(no title)")
        author = str((issue.get("user") or {}).get("login") or "unknown")
        labels = [str(label.get("name") or "") for label in issue.get("labels", [])]
        label_text = ", ".join(label for label in labels if label) or "none"
        issue_url = str(issue.get("html_url") or "")
        if not issue_url.startswith("https://github.com/"):
            raise SlackError(f"Issue #{number} has an unexpected GitHub URL.")

        text = (
            f"New issue in {_safe_mrkdwn(repo)}: {_safe_mrkdwn(title)}\n"
            f"{_safe_mrkdwn(issue_url)}"
        )
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "New GitHub issue", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "plain_text", "text": title},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Repository*\n`{_safe_mrkdwn(repo)}`"},
                    {"type": "mrkdwn", "text": f"*Author*\n{_safe_mrkdwn(author)}"},
                    {"type": "mrkdwn", "text": f"*Issue*\n#{number}"},
                    {"type": "mrkdwn", "text": f"*Labels*\n{_safe_mrkdwn(label_text[:1500])}"},
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Open issue", "emoji": True},
                        "url": issue_url,
                    }
                ],
            },
        ]
        body = json.dumps({"text": text, "blocks": blocks}).encode("utf-8")
        request = Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=20) as response:
                response_body = response.read().decode("utf-8", errors="replace").strip()
                if response.status >= 300 or (response_body and response_body != "ok"):
                    raise SlackError(f"Slack rejected the notification: HTTP {response.status} {response_body}")
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace").strip()
            raise SlackError(f"Slack returned HTTP {exc.code}: {response_body}") from exc
        except (URLError, TimeoutError) as exc:
            raise SlackError(f"Could not send the Slack notification: {exc}") from exc

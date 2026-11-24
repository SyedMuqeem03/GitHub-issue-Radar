"""Configuration loading and validation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class ConfigurationError(ValueError):
    """Raised when required settings are missing or invalid."""


def _load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding environment variables."""
    if not path.is_file():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigurationError(f"Invalid .env entry on line {line_number}: expected KEY=VALUE")

        key, value = (part.strip() for part in line.split("=", 1))
        if not key:
            raise ConfigurationError(f"Invalid .env entry on line {line_number}: missing key")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Config:
    repos: tuple[str, ...]
    slack_webhook_url: str
    poll_interval_seconds: int
    database_path: Path
    github_token: str | None

    @classmethod
    def load(cls) -> "Config":
        _load_dotenv(PROJECT_ROOT / ".env")

        raw_repos = os.environ.get("GITHUB_REPOS", "")
        repos: list[str] = []
        for raw_repo in raw_repos.split(","):
            repo = raw_repo.strip()
            if not repo:
                continue
            if not REPO_PATTERN.fullmatch(repo):
                raise ConfigurationError(
                    f"Invalid repository '{repo}'. Use owner/repository, for example octocat/Hello-World."
                )
            if repo not in repos:
                repos.append(repo)

        if not repos:
            raise ConfigurationError("Set GITHUB_REPOS to one or more public owner/repository names.")

        webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
        if not webhook_url.startswith("https://"):
            raise ConfigurationError("Set SLACK_WEBHOOK_URL to your HTTPS Slack incoming webhook URL.")

        raw_interval = os.environ.get("POLL_INTERVAL_SECONDS", "300").strip()
        try:
            interval = int(raw_interval)
        except ValueError as exc:
            raise ConfigurationError("POLL_INTERVAL_SECONDS must be a whole number of seconds.") from exc
        if interval < 30:
            raise ConfigurationError("POLL_INTERVAL_SECONDS must be at least 30 seconds.")

        raw_database_path = os.environ.get("DATABASE_PATH", "data/issue-scout.sqlite3").strip()
        database_path = Path(raw_database_path)
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path

        token = os.environ.get("GITHUB_TOKEN", "").strip() or None
        return cls(
            repos=tuple(repos),
            slack_webhook_url=webhook_url,
            poll_interval_seconds=interval,
            database_path=database_path,
            github_token=token,
        )

"""Small GitHub REST API client for public repository issues."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


PER_PAGE = 100
API_VERSION = "2022-11-28"


class GitHubApiError(RuntimeError):
    """Raised when GitHub returns an error or an unreadable response."""


class GitHubApi:
    def __init__(self, token: str | None = None) -> None:
        self.token = token

    def list_issues(self, repo: str, page: int) -> list[dict[str, Any]]:
        owner, name = repo.split("/", 1)
        query = urlencode(
            {
                "state": "all",
                "sort": "created",
                "direction": "desc",
                "per_page": PER_PAGE,
                "page": page,
            }
        )
        url = (
            f"https://api.github.com/repos/{quote(owner, safe='')}/"
            f"{quote(name, safe='')}/issues?{query}"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "issue-scout/0.1.0",
            "X-GitHub-Api-Version": API_VERSION,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise GitHubApiError(f"GitHub returned HTTP {exc.code} for {repo}: {body}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GitHubApiError(f"Could not read issues from {repo}: {exc}") from exc

        if not isinstance(payload, list):
            raise GitHubApiError(f"GitHub returned an unexpected response for {repo}.")
        return payload

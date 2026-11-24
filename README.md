# Issue Scout

Issue Scout watches public GitHub repositories and sends a Slack message when a new issue is opened. It does not claim issues or make decisions for you: open the notification, review the issue, and decide whether you want to contribute.

The first run quietly records each repository's current issue number so you won't get a flood of old issues. Later runs alert only for newer issues. Pull requests are filtered out.

## Setup

Requirements: Python 3.10 or newer. The project uses only the Python standard library.

1. Create a Slack app, enable **Incoming Webhooks**, add a webhook for the channel where you want alerts, and copy its URL. Keep that URL secret.
2. Copy `.env.example` to `.env` and configure it:

   ```dotenv
   GITHUB_REPOS=python/cpython,microsoft/vscode
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
   POLL_INTERVAL_SECONDS=300
   DATABASE_PATH=data/issue-scout.sqlite3
   # Optional, but recommended if you watch many repositories:
   # GITHUB_TOKEN=github_pat_your_token
   ```

3. Start the watcher from this directory:

   ```powershell
   py -m issue_scout
   ```

   On macOS or Linux, use `python3 -m issue_scout`.

The watcher checks immediately when it starts, then repeats at the configured interval. Keep the process running to receive alerts. For alerts while your computer is off, run it on an always-on server. Press `Ctrl+C` to stop it.

## Run with GitHub Actions

The repository includes a scheduled workflow that checks the configured repositories every five minutes. GitHub-hosted runners are temporary, so the workflow restores and saves the SQLite scan state using the Actions cache. The first run quietly establishes a baseline.

In the repository's **Settings → Secrets and variables → Actions**, add:

- Repository variable `GITHUB_REPOS`: comma-separated `owner/repository` names, such as `python/cpython,kubernetes/minikube`.
- Repository secret `SLACK_WEBHOOK_URL`: your Slack incoming webhook URL.
- Optional repository secret `ISSUE_SCOUT_GITHUB_TOKEN`: a read-only GitHub token if the public API rate limit is reached.

Keep `.env` on your computer and out of GitHub. The Actions workflow reads its settings from the repository variable and secrets above. Once those are set, use **Actions → Issue Scout → Run workflow** for the first check; later checks run on schedule. Scheduled runs can be delayed during busy periods.

## Configuration

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `GITHUB_REPOS` | Yes | — | Comma-separated `owner/repository` names for public repositories. |
| `SLACK_WEBHOOK_URL` | Yes | — | Slack incoming webhook URL. |
| `POLL_INTERVAL_SECONDS` | No | `300` | Seconds between checks; minimum is 30. |
| `DATABASE_PATH` | No | `data/issue-scout.sqlite3` | SQLite file used to remember the scan position and sent alerts. Relative paths are based on this project directory. |
| `GITHUB_TOKEN` | No | — | Optional GitHub token for higher API request limits. Read-only access to public issues is enough. |

Issue Scout uses GitHub's public Issues API, so repository owners do not need to install an app or configure webhooks. Checks are periodic, so alerts may take up to one poll interval to arrive. The first run establishes a baseline; it does not send alerts for existing issues.

## How it works

- Reads the watched repositories from `.env` or the process environment.
- Checks all issue states, so an issue that closes between checks can still be found.
- Ignores pull requests, which GitHub also includes in issue-list API responses.
- Sends a Slack message with the repository, title, author, labels, and an **Open issue** button.
- Stores progress in SQLite so restarts don't resend previously handled issues.

This first version is a polling process, not a hosted service. The next useful step after trying it is to decide whether you want deployment instructions or more watchlist and filtering controls.

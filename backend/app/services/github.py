"""
Thin GitHub REST client used by the completion-check node and the API layer.

We deliberately avoid the PyGithub dep — every call here is a plain HTTPS
GET, so `requests` is enough and keeps install-time light.
"""
from __future__ import annotations

from typing import List, Optional
import logging
import requests

from app.config import GITHUB_TOKEN
from app.utils.helpers import parse_github_url

logger = logging.getLogger(__name__)

API = "https://api.github.com"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "ai-teacher-agent"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _owner_repo(url: str) -> tuple[str, str]:
    parsed = parse_github_url(url)
    if not parsed:
        raise ValueError(f"Not a valid GitHub URL: {url!r}")
    return parsed


def repo_exists(url: str) -> bool:
    try:
        owner, repo = _owner_repo(url)
    except ValueError:
        return False
    r = requests.get(f"{API}/repos/{owner}/{repo}", headers=_headers(), timeout=10)
    return r.status_code == 200


def list_commits(url: str, branch: str = "main", limit: int = 5) -> List[dict]:
    """Return up to `limit` most-recent commits on the given branch."""
    owner, repo = _owner_repo(url)
    r = requests.get(
        f"{API}/repos/{owner}/{repo}/commits",
        headers=_headers(),
        params={"sha": branch, "per_page": limit},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def compare(url: str, base: str, head: str) -> dict:
    """Return the diff payload between two commit SHAs or refs."""
    owner, repo = _owner_repo(url)
    r = requests.get(
        f"{API}/repos/{owner}/{repo}/compare/{base}...{head}",
        headers=_headers(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def changed_files(url: str, branch: str = "main") -> Optional[List[str]]:
    """
    Return the list of file paths changed between the two most recent commits
    on `branch`, or None when the repo has fewer than two commits.
    """
    commits = list_commits(url, branch=branch, limit=2)
    if len(commits) < 2:
        return None
    head, base = commits[0]["sha"], commits[1]["sha"]
    diff = compare(url, base=base, head=head)
    return [f["filename"] for f in diff.get("files", [])]

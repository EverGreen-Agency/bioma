from datetime import datetime, timezone

import httpx


class GitHubReadError(RuntimeError):
    pass


class GitHubWriteError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com", http_client: httpx.Client | None = None):
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=20,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def project_activity(self, owner: str, repository: str, branch: str, limit: int) -> dict:
        repo_path = f"/repos/{owner}/{repository}"
        issues = self._get(f"{repo_path}/issues", params={"state": "all", "per_page": limit})
        pulls = self._get(f"{repo_path}/pulls", params={"state": "all", "per_page": limit})
        commits = self._get(f"{repo_path}/commits", params={"sha": branch, "per_page": limit})
        return {
            "fetched_at": datetime.now(timezone.utc),
            "issues": [self._issue(item) for item in issues if "pull_request" not in item],
            "pull_requests": [self._pull(item) for item in pulls],
            "commits": [self._commit(item) for item in commits],
        }

    def create_issue(self, owner: str, repository: str, title: str, body: str | None) -> dict:
        path = f"/repos/{owner}/{repository}/issues"
        try:
            response = self._client.post(path, json={"title": title, "body": body or ""})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GitHubWriteError("Não foi possível criar a issue no GitHub.") from exc
        return {"number": payload["number"], "url": payload["html_url"]}

    def find_issue_by_title_prefix(self, owner: str, repository: str, prefix: str) -> dict | None:
        path = f"/repos/{owner}/{repository}/issues"
        issues = self._get(path, params={"state": "all", "per_page": 100})
        for issue in issues:
            if "pull_request" in issue:
                continue
            if str(issue.get("title", "")).startswith(prefix):
                return {"number": issue["number"], "url": issue["html_url"]}
        return None

    def _get(self, path: str, params: dict) -> list[dict]:
        try:
            response = self._client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GitHubReadError("Não foi possível consultar o repositório GitHub.") from exc
        if not isinstance(payload, list):
            raise GitHubReadError("Resposta inesperada da API do GitHub.")
        return payload

    @staticmethod
    def _issue(item: dict) -> dict:
        return {
            "number": item["number"], "title": item["title"], "state": item["state"],
            "url": item["html_url"], "labels": [label["name"] for label in item.get("labels", [])],
            "updated_at": item["updated_at"],
        }

    @staticmethod
    def _pull(item: dict) -> dict:
        return {
            "number": item["number"], "title": item["title"], "state": item["state"],
            "draft": bool(item.get("draft")), "url": item["html_url"],
            "source_branch": item["head"]["ref"], "target_branch": item["base"]["ref"],
            "updated_at": item["updated_at"],
        }

    @staticmethod
    def _commit(item: dict) -> dict:
        commit = item.get("commit", {})
        author = commit.get("author") or {}
        return {
            "sha": item["sha"], "message": (commit.get("message") or "").splitlines()[0],
            "url": item["html_url"], "author_name": author.get("name"), "authored_at": author.get("date"),
        }

import logging
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
from app.core.models import Finding, PRMetadata

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Client for interacting with GitHub Pull Requests API.
    Supports live GitHub App / Personal Access Token, or Simulation Mode when tokens are omitted.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    @property
    def is_simulation(self) -> bool:
        return not bool(self.token)

    def is_simulation_target(self, owner: str, repo: str) -> bool:
        if self.is_simulation:
            return True
        sim_keywords = ("demo", "local", "benchmark", "test", "sample", "example")
        return any(k in owner.lower() for k in sim_keywords) or any(k in repo.lower() for k in sim_keywords)

    async def get_pr_metadata(self, owner: str, repo: str, pull_number: int) -> PRMetadata:
        if self.is_simulation_target(owner, repo):
            logger.info("Simulation mode: generating mock PR metadata")
            return PRMetadata(
                repo_owner=owner,
                repo_name=repo,
                pr_number=pull_number,
                title="Simulated Pull Request",
                description="Simulated pull request description for local evaluation.",
                author="developer",
                head_sha="head12345",
                base_sha="base12345",
            )

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return PRMetadata(
                repo_owner=owner,
                repo_name=repo,
                pr_number=pull_number,
                title=data.get("title", ""),
                description=data.get("body", "") or "",
                author=data.get("user", {}).get("login", ""),
                head_sha=data.get("head", {}).get("sha", ""),
                base_sha=data.get("base", {}).get("sha", ""),
            )

    async def get_pr_diff(self, owner: str, repo: str, pull_number: int) -> str:
        if self.is_simulation_target(owner, repo):
            return ""

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = dict(self.headers)
        headers["Accept"] = "application/vnd.github.v3.diff"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    async def post_review(
        self,
        metadata: PRMetadata,
        findings: List[Finding],
        summary_markdown: str,
    ) -> Dict[str, Any]:
        """
        Posts inline review comments using GitHub's Pull Request Review API.
        Includes ```suggestion markdown for actionable code fixes.
        """
        comments = []
        for finding in findings:
            body = f"**[{finding.category.upper()}]** {finding.comment}\n\n*Severity: `{finding.severity}` | Confidence: `{int(finding.confidence * 100)}%`*"
            if finding.suggested_fix:
                body += f"\n\n```suggestion\n{finding.suggested_fix}\n```"

            comments.append({
                "path": finding.file,
                "line": finding.line,
                "body": body,
            })

        if self.is_simulation_target(metadata.repo_owner, metadata.repo_name):
            logger.info(
                f"[SIMULATION] Posted review for PR #{metadata.pr_number} with {len(comments)} inline comments."
            )
            return {
                "status": "simulated",
                "summary": summary_markdown,
                "comments_count": len(comments),
                "comments": comments,
            }

        url = f"https://api.github.com/repos/{metadata.repo_owner}/{metadata.repo_name}/pulls/{metadata.pr_number}/reviews"
        payload = {
            "commit_id": metadata.head_sha,
            "body": summary_markdown,
            "event": "COMMENT",
            "comments": comments,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            resp.raise_for_status()
            return resp.json()

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from app.core.config import settings
from app.graph.workflow import build_pr_review_graph

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verifies that the webhook payload came from GitHub using HMAC-SHA256.
    """
    if not settings.github_webhook_secret:
        # If secret not set in local dev, allow passing
        return True

    if not signature_header:
        return False

    hash_type, signature = signature_header.split("=")
    if hash_type != "sha256":
        return False

    mac = hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )
    return hmac.compare_digest(mac.hexdigest(), signature)


async def process_pr_review_task(payload: dict):
    """
    Background worker that runs the LangGraph PR review workflow.
    """
    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})

    pr_number = pr_data.get("number")
    repo_owner = repo_data.get("owner", {}).get("login", "")
    repo_name = repo_data.get("name", "")

    from app.github.client import GitHubClient
    client = GitHubClient()
    diff = await client.get_pr_diff(repo_owner, repo_name, pr_number)

    state_input = {
        "pr_id": f"{repo_owner}/{repo_name}#{pr_number}",
        "repo_owner": repo_owner,
        "repo_name": repo_name,
        "pr_number": pr_number,
        "diff": diff,
        "pr_metadata": {
            "title": pr_data.get("title", ""),
            "description": pr_data.get("body", "") or "",
            "author": pr_data.get("user", {}).get("login", ""),
            "head_sha": pr_data.get("head", {}).get("sha", ""),
            "base_sha": pr_data.get("base", {}).get("sha", ""),
        },
        "changed_files": [],
        "triage": {},
        "context": {},
        "static_analysis": {},
        "findings": [],
        "deduped_findings": [],
        "verified": [],
        "approved": [],
        "review_summary": "",
        "posted": False,
        "requires_human_approval": False,
    }

    graph = build_pr_review_graph()
    try:
        final_state = graph.invoke(
            state_input,
            {"configurable": {"thread_id": f"{repo_owner}-{repo_name}-{pr_number}"}},
        )
        logger.info(
            f"Completed PR #{pr_number} review: {len(final_state.get('approved', []))} findings posted."
        )
    except Exception as e:
        logger.error(f"Error processing PR review workflow: {e}")


@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(default=None),
    x_github_event: str = Header(default=None),
):
    body = await request.body()

    if not verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook HMAC-SHA256 signature",
        )

    # Only process pull_request events
    if x_github_event != "pull_request":
        return {"status": "ignored", "event": x_github_event}

    payload = json.loads(body.decode("utf-8"))
    action = payload.get("action")

    # Trigger on opened, synchronize (new commits), or reopened
    if action in ["opened", "synchronize", "reopened"]:
        background_tasks.add_task(process_pr_review_task, payload)
        return {"status": "enqueued", "action": action, "pr_number": payload.get("pull_request", {}).get("number")}

    return {"status": "skipped", "action": action}

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.graph.workflow import build_pr_review_graph
from app.core.models import FindingFeedback
from app.feedback.learnings import LearningsStore

logger = logging.getLogger(__name__)
router = APIRouter()


class DirectReviewRequest(BaseModel):
    diff: str
    title: str = "Pull Request"
    description: str = ""
    repo_owner: str = "local-org"
    repo_name: str = "local-repo"
    pr_number: int = 1


@router.post("/review")
async def trigger_direct_review(req: DirectReviewRequest):
    """
    Directly run the PR review pipeline on raw diff input (for CLI, CI, or local testing).
    """
    state_input = {
        "pr_id": f"{req.repo_owner}/{req.repo_name}#{req.pr_number}",
        "repo_owner": req.repo_owner,
        "repo_name": req.repo_name,
        "pr_number": req.pr_number,
        "diff": req.diff,
        "pr_metadata": {
            "title": req.title,
            "description": req.description,
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
            {"configurable": {"thread_id": f"direct-{req.pr_number}"}},
        )
        return {
            "pr_id": final_state.get("pr_id"),
            "triage": final_state.get("triage"),
            "verified_count": len(final_state.get("verified", [])),
            "approved_count": len(final_state.get("approved", [])),
            "findings": final_state.get("approved", []),
            "summary": final_state.get("review_summary"),
        }
    except Exception as e:
        logger.error(f"Review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(feedback: FindingFeedback):
    """
    Records human approval or rejection to update team learnings and ML ranking.
    """
    store = LearningsStore()
    store.record_feedback(feedback)
    return {"status": "recorded", "action": feedback.action}

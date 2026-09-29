import logging
from typing import Any

from pydantic import BaseModel, Field

from app.core.llm import invoke_structured_llm
from app.graph.state import ReviewState

logger = logging.getLogger(__name__)


class TriageResult(BaseModel):
    pr_type: str = Field(description="feature, bugfix, refactor, docs, chore")
    size_category: str = Field(description="small, medium, large")
    risk_level: str = Field(description="low, medium, high")
    active_specialists: list[str] = Field(
        description="List of specialists to activate: bug, security, performance, tests, style"
    )
    rationale: str = Field(description="Explanation for triage classification")


def triage_node(state: ReviewState) -> dict[str, Any]:
    changed_files = state.get("changed_files", [])
    diff = state.get("diff", "")
    metadata = state.get("pr_metadata", {})
    title = metadata.get("title", "")
    description = metadata.get("description", "")

    # Fast heuristic check for docs-only PRs
    is_docs_only = bool(changed_files) and all(
        f.endswith(".md") or f.endswith(".txt") or f.endswith(".rst") or "docs/" in f
        for f in changed_files
    )

    if is_docs_only:
        triage = TriageResult(
            pr_type="docs",
            size_category="small" if len(diff.splitlines()) < 200 else "medium",
            risk_level="low",
            active_specialists=["style"],
            rationale="Documentation-only pull request. Skipping code, security, and performance agents.",
        )
        return {"triage": triage.model_dump()}

    prompt = f"""
Analyze this Pull Request to determine its type, risk, and which specialist reviewers to run.
Title: {title}
Description: {description}
Changed Files: {', '.join(changed_files)}

Diff snippet (first 100 lines):
{chr(10).join(diff.splitlines()[:100])}
"""

    system_prompt = (
        "You are an expert PR triage system. Categorize PRs and pick relevant specialists from: "
        "['bug', 'security', 'performance', 'tests', 'style']."
    )

    try:
        triage = invoke_structured_llm(
            prompt=prompt,
            output_schema=TriageResult,
            system_prompt=system_prompt,
        )
        logger.info(f"Triage complete: {triage.pr_type} ({triage.risk_level} risk), specialists: {triage.active_specialists}")
        return {"triage": triage.model_dump()}
    except Exception as e:
        logger.warning(f"LLM triage fallback to default: {e}")
        # Robust fallback
        default_specialists = ["bug", "security", "performance", "tests", "style"]
        return {
            "triage": {
                "pr_type": "feature",
                "size_category": "medium",
                "risk_level": "medium",
                "active_specialists": default_specialists,
                "rationale": "Default triage applied.",
            }
        }

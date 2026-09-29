import operator
from typing import Annotated, Any, TypedDict

from app.core.models import Finding


class ReviewState(TypedDict):
    pr_id: str
    repo_owner: str
    repo_name: str
    pr_number: int
    diff: str
    pr_metadata: dict[str, Any]
    changed_files: list[str]
    triage: dict[str, Any]
    context: dict[str, Any]
    static_analysis: dict[str, Any]
    findings: Annotated[list[Finding], operator.add]
    deduped_findings: list[Finding]
    verified: list[Finding]
    approved: list[Finding]
    review_summary: str
    posted: bool
    requires_human_approval: bool

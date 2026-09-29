from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from app.core.models import Finding


class ReviewState(TypedDict):
    pr_id: str
    repo_owner: str
    repo_name: str
    pr_number: int
    diff: str
    pr_metadata: Dict[str, Any]
    changed_files: List[str]
    triage: Dict[str, Any]
    context: Dict[str, Any]
    static_analysis: Dict[str, Any]
    findings: Annotated[List[Finding], operator.add]
    deduped_findings: List[Finding]
    verified: List[Finding]
    approved: List[Finding]
    review_summary: str
    posted: bool
    requires_human_approval: bool

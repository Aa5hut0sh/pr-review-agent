from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Finding(BaseModel):
    file: str = Field(description="Relative path of the changed file")
    line: int = Field(description="Line number in the changed file (from diff)")
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="Severity level of the issue"
    )
    category: Literal["bug", "security", "performance", "tests", "style"] = Field(
        description="Category classification of the finding"
    )
    comment: str = Field(description="Clear explanation of the problem and reason")
    suggested_fix: Optional[str] = Field(
        default=None,
        description="Concrete replacement code snippet or suggestion block"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Code snippets, static tool output, or retrieved context evidence"
    )


class PRMetadata(BaseModel):
    repo_owner: str
    repo_name: str
    pr_number: int
    title: str
    description: str = ""
    author: str = ""
    head_sha: str = ""
    base_sha: str = ""


class DiffHunk(BaseModel):
    file: str
    old_start: int
    new_start: int
    hunk_header: str
    diff_lines: List[str]
    added_lines: List[tuple[int, str]] = Field(
        default_factory=list,
        description="List of (line_number, line_content) for newly added/modified lines"
    )


class FindingFeedback(BaseModel):
    finding_id: str
    action: Literal["approved", "rejected", "edited", "dismissed"]
    feedback_text: Optional[str] = None
    repo: str
    category: str
    severity: str

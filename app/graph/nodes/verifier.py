import logging
from typing import Any

from pydantic import BaseModel, Field

from app.core.llm import invoke_structured_llm
from app.core.models import Finding
from app.github.diff_parser import DiffParser
from app.graph.state import ReviewState

logger = logging.getLogger(__name__)


class VerificationDecision(BaseModel):
    is_valid: bool = Field(description="True if finding is genuine, actionable and verified")
    reason: str = Field(description="Reason why the finding was accepted or rejected")
    adjusted_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score after critic evaluation"
    )


class VerificationBatchResult(BaseModel):
    results: list[VerificationDecision] = Field(default_factory=list)


def is_line_in_diff(file: str, line: int, parsed_diff: dict[str, Any]) -> bool:
    """
    Checks if a target line exists within the added/changed lines or context of the diff.
    """
    if file not in parsed_diff:
        # Check without leading slashes
        clean_file = file.lstrip("./")
        matched_key = next((k for k in parsed_diff if k.endswith(clean_file) or clean_file.endswith(k)), None)
        if not matched_key:
            return False
        hunks = parsed_diff[matched_key]
    else:
        hunks = parsed_diff[file]

    for hunk in hunks:
        # Check if line is within the hunk's range
        hunk_end = hunk.new_start + len(hunk.diff_lines)
        if hunk.new_start <= line <= hunk_end:
            return True
    return False


def verifier_node(state: ReviewState) -> dict[str, Any]:
    """
    Critic Node: filters out hallucinations, unsupported claims, and invalid line references.
    """
    deduped = state.get("deduped_findings", [])
    if not deduped:
        return {"verified": []}

    diff = state.get("diff", "")
    parsed_diff = DiffParser.parse(diff)

    # 1. Programmatic line & file validation
    candidates: list[Finding] = []
    for f in deduped:
        if not is_line_in_diff(f.file, f.line, parsed_diff):
            logger.info(f"Verifier dropped finding at {f.file}:{f.line} - line not present in diff.")
            continue
        candidates.append(f)

    if not candidates:
        return {"verified": []}

    # 2. LLM Critic Verification
    # Prompt the critic with code diff, context, and candidates
    findings_prompt_items = []
    for idx, f in enumerate(candidates):
        findings_prompt_items.append(
            f"Finding #{idx}:\n"
            f"- File: {f.file}\n"
            f"- Line: {f.line}\n"
            f"- Category: {f.category}\n"
            f"- Severity: {f.severity}\n"
            f"- Comment: {f.comment}\n"
            f"- Fix: {f.suggested_fix or 'None'}\n"
        )

    prompt = f"""
You are the Verifier (Critic) for an AI PR Review system.
Your job is to eliminate false positives, nitpicks, and hallucinations.

For EACH candidate finding below, decide if it should be ACCEPTED (is_valid=true) or REJECTED (is_valid=false).
A finding MUST be rejected if:
- The claim is factually unsupported by the code in <diff>.
- It is already handled elsewhere (e.g., validated higher up or in caller).
- It is a subjective aesthetic nitpick or style preference with no real risk.

<diff>
{diff}
</diff>

Candidate findings to verify:
{chr(10).join(findings_prompt_items)}

Return a VerificationBatchResult with an array of VerificationDecision corresponding 1:1 to each candidate finding in exact order.
"""

    system_prompt = (
        "You are an adversarial code review critic. Your goal is high precision: "
        "only keep findings that represent real, impactful bugs, vulnerabilities, or regressions."
    )

    try:
        verification = invoke_structured_llm(
            prompt=prompt,
            output_schema=VerificationBatchResult,
            system_prompt=system_prompt,
        )

        verified: list[Finding] = []
        for f, decision in zip(candidates, verification.results):
            if decision.is_valid and decision.adjusted_confidence >= 0.5:
                f.confidence = decision.adjusted_confidence
                f.evidence.append(f"Verifier: {decision.reason}")
                verified.append(f)
            else:
                logger.info(f"Verifier rejected finding at {f.file}:{f.line} - {decision.reason}")

        logger.info(f"Verifier verified {len(verified)} out of {len(candidates)} candidates.")
        return {"verified": verified}
    except Exception as e:
        logger.warning(f"Verifier LLM call failed ({e}); falling back to confidence-based filtering.")
        # Fallback: keep candidates with confidence >= 0.7
        verified = [f for f in candidates if f.confidence >= 0.7]
        return {"verified": verified}

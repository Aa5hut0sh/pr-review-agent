import logging
from typing import Any

from app.core.models import Finding
from app.graph.state import ReviewState

logger = logging.getLogger(__name__)


def hitl_node(state: ReviewState) -> dict[str, Any]:
    """
    Human-in-the-Loop node:
    Flags findings with critical/high severity or borderline confidence for human approval.
    Automates approval for safe, high-confidence findings.
    """
    verified: list[Finding] = state.get("verified", [])

    risky_findings = []
    auto_approved = []

    for f in verified:
        # Require human review for critical or high severity, or confidence below 0.80
        if f.severity in ["critical", "high"] or f.confidence < 0.80:
            risky_findings.append(f)
        else:
            auto_approved.append(f)

    requires_human = len(risky_findings) > 0

    logger.info(
        f"HITL check: {len(auto_approved)} auto-approved, {len(risky_findings)} require human sign-off."
    )

    # In default auto-flow, if no interactive interrupt occurs, approved = auto_approved + risky
    # When reviewed via dashboard, approved is replaced with the maintainer's selections
    return {
        "requires_human_approval": requires_human,
        "approved": verified if not requires_human else auto_approved,
    }

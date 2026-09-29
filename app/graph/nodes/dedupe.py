import logging
from typing import Any

from app.core.models import Finding
from app.graph.state import ReviewState

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def dedupe_node(state: ReviewState) -> dict[str, Any]:
    raw_findings: list[Finding] = state.get("findings", [])
    if not raw_findings:
        return {"deduped_findings": []}

    # Group by (file, line)
    grouped: dict[tuple[str, int], list[Finding]] = {}
    for f in raw_findings:
        key = (f.file.strip(), f.line)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(f)

    deduped: list[Finding] = []
    for key, group in grouped.items():
        if len(group) == 1:
            deduped.append(group[0])
        else:
            # Pick highest severity
            best = max(
                group,
                key=lambda item: (
                    SEVERITY_ORDER.get(item.severity, 1),
                    item.confidence,
                ),
            )
            # Combine evidence from others
            combined_evidence = set(best.evidence)
            for other in group:
                combined_evidence.update(other.evidence)
            best.evidence = list(combined_evidence)
            deduped.append(best)

    # Rank by severity desc, confidence desc
    deduped.sort(
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 1),
            item.confidence,
        ),
        reverse=True,
    )

    logger.info(f"Deduped {len(raw_findings)} raw findings down to {len(deduped)} distinct findings.")
    return {"deduped_findings": deduped}

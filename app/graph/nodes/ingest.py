import logging
from typing import Dict, Any
from app.graph.state import ReviewState
from app.github.diff_parser import DiffParser

logger = logging.getLogger(__name__)


def ingest_node(state: ReviewState) -> Dict[str, Any]:
    """
    Ingests diff, parses files, filters out binaries and lockfiles.
    """
    raw_diff = state.get("diff", "")
    parsed_files = DiffParser.parse(raw_diff)
    changed_files = list(parsed_files.keys())

    logger.info(f"Ingested PR #{state.get('pr_number')}: {len(changed_files)} relevant changed files.")

    return {
        "changed_files": changed_files,
        "findings": [],
        "deduped_findings": [],
        "verified": [],
        "approved": [],
        "posted": False,
        "requires_human_approval": False,
    }

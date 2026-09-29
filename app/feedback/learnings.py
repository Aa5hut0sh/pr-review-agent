import json
import logging
from typing import List, Dict, Any, Optional
from app.indexing.vector_store import VectorStore
from app.core.models import FindingFeedback

logger = logging.getLogger(__name__)


class LearningsStore:
    """
    Manages persistent learnings and preferences from human feedback.
    Stores feedback examples in vector store to guide future reviews.
    """

    def __init__(self):
        self.vector_store = VectorStore(collection_name="team_learnings")

    def record_feedback(self, feedback: FindingFeedback):
        """
        Records human feedback (approved, rejected, dismissed, edited) for a finding.
        """
        text = (
            f"Action: {feedback.action}. "
            f"Category: {feedback.category}. "
            f"Severity: {feedback.severity}. "
            f"Feedback: {feedback.feedback_text or 'No specific note.'}"
        )
        self.vector_store.add_chunks([{
            "text": text,
            "metadata": {
                "action": feedback.action,
                "category": feedback.category,
                "severity": feedback.severity,
                "repo": feedback.repo,
            }
        }])
        logger.info(f"Recorded feedback: {feedback.action} for {feedback.category}")

    def get_relevant_learnings(self, context_query: str, limit: int = 3) -> List[str]:
        """
        Retrieves relevant learnings based on the current PR context.
        """
        results = self.vector_store.search(query=context_query, limit=limit)
        return [
            hit.get("payload", {}).get("text", "")
            for hit in results
            if hit.get("payload", {}).get("text")
        ]

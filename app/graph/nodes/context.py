import logging
import shutil
import subprocess
from typing import Any

from app.feedback.learnings import LearningsStore
from app.graph.state import ReviewState
from app.indexing.code_graph import CodeGraph
from app.indexing.vector_store import VectorStore

logger = logging.getLogger(__name__)


def run_static_analysis(changed_files: list[str]) -> dict[str, Any]:
    """
    Runs static analysis (e.g., ruff for Python) on changed files if available.
    """
    results = {}
    py_files = [f for f in changed_files if f.endswith(".py")]
    if not py_files:
        return results

    if shutil.which("ruff"):
        try:
            cmd = ["ruff", "check", "--output-format=json"] + py_files
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            results["ruff"] = res.stdout if res.stdout else res.stderr
        except Exception as e:
            results["ruff_error"] = str(e)
    return results


def context_node(state: ReviewState) -> dict[str, Any]:
    diff = state.get("diff", "")
    changed_files = state.get("changed_files", [])

    vector_store = VectorStore()
    code_graph = CodeGraph()
    learnings_store = LearningsStore()

    # 1. Vector Search for relevant code & conventions
    query_text = diff[:1000] if diff else "code conventions"
    vector_hits = vector_store.search(query=query_text, limit=3)

    # 2. Graph Blast Radius Query
    # Extract function names touched in files
    entities_to_query = [
        f.split("/")[-1].replace(".py", "") for f in changed_files
    ]
    blast_radius = code_graph.get_blast_radius(entities_to_query)

    # 3. Retrieve Team Learnings
    learnings = learnings_store.get_relevant_learnings(context_query=query_text)

    # 4. Static analysis
    static_analysis = run_static_analysis(changed_files)

    context_data = {
        "vector_hits": [hit.get("payload", {}) for hit in vector_hits],
        "blast_radius": blast_radius,
        "learnings": learnings,
        "static_analysis": static_analysis,
    }

    logger.info(
        f"Context assembled: {len(vector_hits)} vector hits, {len(blast_radius.get('callers', []))} graph callers, {len(learnings)} learnings."
    )

    return {
        "context": context_data,
        "static_analysis": static_analysis,
    }

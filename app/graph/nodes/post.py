import logging
import asyncio
from typing import Dict, Any, List
from app.graph.state import ReviewState
from app.core.models import Finding, PRMetadata
from app.github.client import GitHubClient

logger = logging.getLogger(__name__)


def generate_pr_summary(
    state: ReviewState,
    approved_findings: List[Finding]
) -> str:
    metadata = state.get("pr_metadata", {})
    triage = state.get("triage", {})
    blast_radius = state.get("context", {}).get("blast_radius", {})
    
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    category_counts = {}

    for f in approved_findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        category_counts[f.category] = category_counts.get(f.category, 0) + 1

    summary = []
    summary.append("## 🤖 AI Pull Request Review\n")
    summary.append(f"**Triage:** `{triage.get('pr_type', 'feature')}` | **Risk:** `{triage.get('risk_level', 'medium')}`\n")
    
    # Blast radius note
    callers = blast_radius.get("callers", [])
    if callers:
        summary.append(f"⚡ **Blast Radius Notice:** {len(callers)} dependent functions may be impacted by these changes ({', '.join(callers[:3])}{'...' if len(callers) > 3 else ''}).\n")

    summary.append("### 📊 Findings Summary\n")
    summary.append("| Category | Critical | High | Medium | Low | Total |")
    summary.append("|---|---|---|---|---|---|")
    
    categories = sorted(list(set(f.category for f in approved_findings)))
    if not categories:
        summary.append("| *All Clean* | 0 | 0 | 0 | 0 | 0 |")
    else:
        for cat in categories:
            cat_findings = [f for f in approved_findings if f.category == cat]
            crit = sum(1 for f in cat_findings if f.severity == "critical")
            hi = sum(1 for f in cat_findings if f.severity == "high")
            med = sum(1 for f in cat_findings if f.severity == "medium")
            lo = sum(1 for f in cat_findings if f.severity == "low")
            total = len(cat_findings)
            summary.append(f"| **{cat.capitalize()}** | {crit} | {hi} | {med} | {lo} | **{total}** |")

    summary.append(f"\n*Total approved inline comments posted: **{len(approved_findings)}***\n")
    summary.append("---")
    summary.append("\n*Reviewed with Multi-Agent LangGraph + Groq LLM.*")

    return "\n".join(summary)


def post_node(state: ReviewState) -> Dict[str, Any]:
    approved_findings = state.get("approved", [])
    summary = generate_pr_summary(state, approved_findings)

    metadata_dict = state.get("pr_metadata", {})
    metadata = PRMetadata(
        repo_owner=state.get("repo_owner", "local-org"),
        repo_name=state.get("repo_name", "local-repo"),
        pr_number=state.get("pr_number", 1),
        title=metadata_dict.get("title", "Pull Request"),
        description=metadata_dict.get("description", ""),
        author=metadata_dict.get("author", "developer"),
        head_sha=metadata_dict.get("head_sha", "HEAD"),
    )

    client = GitHubClient()
    try:
        # Run async call synchronously in worker/sync node
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()

        loop.run_until_complete(
            client.post_review(
                metadata=metadata,
                findings=approved_findings,
                summary_markdown=summary,
            )
        )
        posted = True
    except Exception as e:
        logger.error(f"Failed to post GitHub review: {e}")
        posted = False

    return {
        "review_summary": summary,
        "posted": posted,
    }

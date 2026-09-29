import logging
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import ReviewState
from app.core.models import Finding
from app.graph.nodes.ingest import ingest_node
from app.graph.nodes.triage import triage_node
from app.graph.nodes.context import context_node
from app.graph.nodes.specialists import run_specialist
from app.graph.nodes.dedupe import dedupe_node
from app.graph.nodes.verifier import verifier_node
from app.graph.nodes.hitl import hitl_node
from app.graph.nodes.post import post_node

logger = logging.getLogger(__name__)


class SpecialistInput(TypedDict):
    role: str
    diff: str
    description: str
    context: Dict[str, Any]
    static_analysis: Dict[str, Any]


def specialist_worker_node(data: SpecialistInput) -> Dict[str, Any]:
    """
    Worker node executed in parallel for each active specialist via LangGraph Send.
    Returns findings which are automatically accumulated via operator.add in ReviewState.
    """
    role = data["role"]
    logger.info(f"Running specialist worker for role: {role}")
    findings = run_specialist(
        role_key=role,
        diff=data["diff"],
        pr_description=data["description"],
        context_data=data["context"],
        static_analysis=data["static_analysis"],
    )
    return {"findings": findings}


def dispatch_specialists(state: ReviewState):
    """
    Fan-out router: dispatches one parallel worker per active specialist determined during triage.
    """
    triage = state.get("triage", {})
    active = triage.get("active_specialists", ["bug", "security", "performance", "tests", "style"])
    desc = state.get("pr_metadata", {}).get("description", "")
    diff = state.get("diff", "")
    ctx = state.get("context", {})
    static_tool_out = state.get("static_analysis", {})

    return [
        Send(
            "specialist_worker",
            {
                "role": role,
                "diff": diff,
                "description": desc,
                "context": ctx,
                "static_analysis": static_tool_out,
            },
        )
        for role in active
    ]


def build_pr_review_graph(checkpointer=None):
    """
    Constructs the end-to-end multi-agent PR review LangGraph.
    """
    workflow = StateGraph(ReviewState)

    # 1. Add core nodes
    workflow.add_node("ingest", ingest_node)
    workflow.add_node("triage", triage_node)
    workflow.add_node("context_builder", context_node)
    workflow.add_node("specialist_worker", specialist_worker_node)
    workflow.add_node("dedupe", dedupe_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("hitl", hitl_node)
    workflow.add_node("post", post_node)

    # 2. Define sequential and fan-out edges
    workflow.add_edge(START, "ingest")
    workflow.add_edge("ingest", "triage")
    workflow.add_edge("triage", "context_builder")

    # Fan-out to parallel specialist workers using Send
    workflow.add_conditional_edges(
        "context_builder",
        dispatch_specialists,
        ["specialist_worker"],
    )

    # All specialist workers join at dedupe
    workflow.add_edge("specialist_worker", "dedupe")
    workflow.add_edge("dedupe", "verifier")
    workflow.add_edge("verifier", "hitl")
    workflow.add_edge("hitl", "post")
    workflow.add_edge("post", END)

    memory = checkpointer or MemorySaver()
    return workflow.compile(checkpointer=memory)

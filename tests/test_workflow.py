from app.graph.workflow import build_pr_review_graph


def test_build_pr_review_graph():
    graph = build_pr_review_graph()
    assert graph is not None

    # Verify node names in the compiled graph
    node_names = set(graph.nodes.keys())
    expected_nodes = {
        "ingest",
        "triage",
        "context_builder",
        "specialist_worker",
        "dedupe",
        "verifier",
        "hitl",
        "post",
    }
    for node in expected_nodes:
        assert node in node_names, f"Node {node} missing from graph nodes"

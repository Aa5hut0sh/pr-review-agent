from app.core.models import Finding
from app.graph.nodes.dedupe import dedupe_node
from app.graph.nodes.verifier import is_line_in_diff
from app.github.diff_parser import DiffParser


def test_dedupe_merges_same_line():
    f1 = Finding(
        file="api/auth.py",
        line=42,
        severity="medium",
        category="security",
        comment="Potential missing token check",
        confidence=0.75,
        evidence=["rule-1"],
    )
    f2 = Finding(
        file="api/auth.py",
        line=42,
        severity="critical",
        category="security",
        comment="Token verification bypassed",
        confidence=0.92,
        evidence=["rule-2"],
    )

    state = {"findings": [f1, f2]}
    res = dedupe_node(state)
    deduped = res["deduped_findings"]
    assert len(deduped) == 1
    # Higher severity should win
    assert deduped[0].severity == "critical"
    assert deduped[0].confidence == 0.92
    assert "rule-1" in deduped[0].evidence
    assert "rule-2" in deduped[0].evidence


def test_verifier_line_in_diff():
    diff = """diff --git a/src/calc.py b/src/calc.py
@@ -10,5 +10,6 @@ def add(a, b):
     return a + b
+    print(1)
"""
    parsed = DiffParser.parse(diff)
    assert is_line_in_diff("src/calc.py", 10, parsed) is True
    assert is_line_in_diff("src/calc.py", 999, parsed) is False
    assert is_line_in_diff("other/file.py", 10, parsed) is False

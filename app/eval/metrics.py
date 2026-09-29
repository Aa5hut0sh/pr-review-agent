from typing import Any

from app.core.models import Finding
from app.eval.synthetic_prs import SyntheticPR


def evaluate_findings(
    synthetic_pr: SyntheticPR,
    predicted_findings: list[Finding],
) -> dict[str, Any]:
    """
    Evaluates agent findings against ground-truth seeded bugs for a single PR.
    """
    ground_truth = list(synthetic_pr.ground_truth_bugs)
    tp = 0
    matched_gt = set()

    for finding in predicted_findings:
        for idx, gt in enumerate(ground_truth):
            if idx in matched_gt:
                continue
            # Match if same file and close line proximity (+- 3 lines) or category match
            if finding.file == gt["file"] and abs(finding.line - gt["line"]) <= 3:
                tp += 1
                matched_gt.add(idx)
                break

    fp = len(predicted_findings) - tp
    fn = len(ground_truth) - len(matched_gt)

    return {
        "pr_id": synthetic_pr.id,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "ground_truth_count": len(ground_truth),
        "predicted_count": len(predicted_findings),
    }


def compute_aggregate_metrics(results: list[dict[str, Any]]) -> dict[str, float]:
    """
    Computes overall Recall, Precision, and FP/PR across a benchmark run.
    """
    total_tp = sum(r["tp"] for r in results)
    total_fp = sum(r["fp"] for r in results)
    total_fn = sum(r["fn"] for r in results)
    total_prs = max(1, len(results))

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    fp_per_pr = total_fp / total_prs

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "fp_per_pr": round(fp_per_pr, 2),
        "total_prs": total_prs,
    }

import logging

import numpy as np
from sklearn.linear_model import LogisticRegression

from app.core.models import Finding

logger = logging.getLogger(__name__)

SEVERITY_MAP = {"low": 0, "medium": 1, "high": 2, "critical": 3}
CATEGORY_MAP = {"style": 0, "tests": 1, "performance": 2, "bug": 3, "security": 4}


class AcceptClassifier:
    """
    Lightweight classifier predicting whether a finding will be accepted by humans.
    Features: [severity_num, category_num, confidence, line_depth_log]
    """

    def __init__(self):
        self.model = LogisticRegression()
        self.is_fitted = False
        self._init_default_model()

    def _extract_features(self, finding: Finding) -> list[float]:
        sev = SEVERITY_MAP.get(finding.severity, 1)
        cat = CATEGORY_MAP.get(finding.category, 0)
        conf = float(finding.confidence)
        line_feat = np.log1p(max(1, finding.line))
        return [sev, cat, conf, line_feat]

    def _init_default_model(self):
        """
        Seed with initial synthetic training weights reflecting high precision priorities:
        Security and high severity bugs have higher acceptance rates than nitpick styles.
        """
        X = np.array([
            # [sev, cat, conf, line]
            [3, 4, 0.95, 2.0],  # critical security -> accepted
            [2, 3, 0.90, 3.0],  # high bug -> accepted
            [1, 3, 0.75, 1.5],  # medium bug -> accepted
            [0, 0, 0.40, 4.0],  # low style nit -> rejected
            [0, 0, 0.50, 1.0],  # low style -> rejected
            [1, 1, 0.85, 2.5],  # medium tests -> accepted
            [1, 0, 0.60, 3.5],  # medium style -> rejected
        ])
        y = np.array([1, 1, 1, 0, 0, 1, 0])
        self.model.fit(X, y)
        self.is_fitted = True

    def train(self, findings: list[Finding], labels: list[int]):
        """
        Re-train on historical human accept/reject feedback labels (1=accepted, 0=rejected).
        """
        if len(findings) < 5 or len(set(labels)) < 2:
            logger.info("Not enough diverse feedback data yet to retrain classifier.")
            return

        X = np.array([self._extract_features(f) for f in findings])
        y = np.array(labels)
        self.model.fit(X, y)
        self.is_fitted = True
        logger.info("Retrained accept-classifier with human feedback dataset.")

    def predict_accept_prob(self, finding: Finding) -> float:
        """
        Returns estimated acceptance probability (0.0 to 1.0).
        """
        if not self.is_fitted:
            return finding.confidence

        features = np.array([self._extract_features(finding)])
        prob = self.model.predict_proba(features)[0][1]
        return float(prob)

    def rank_and_filter(self, findings: list[Finding], min_prob: float = 0.3) -> list[Finding]:
        """
        Ranks findings by acceptance probability and suppresses those below min_prob.
        """
        scored = [(f, self.predict_accept_prob(f)) for f in findings]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [f for f, prob in scored if prob >= min_prob]

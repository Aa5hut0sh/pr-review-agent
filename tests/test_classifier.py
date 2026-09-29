from app.core.models import Finding
from app.feedback.classifier import AcceptClassifier


def test_accept_classifier_ranking():
    clf = AcceptClassifier()

    crit_security = Finding(
        file="auth.py",
        line=12,
        severity="critical",
        category="security",
        comment="Critical SQL injection vulnerability",
        confidence=0.98,
    )
    low_style = Finding(
        file="utils.py",
        line=150,
        severity="low",
        category="style",
        comment="Prefer trailing commas here",
        confidence=0.45,
    )

    p_crit = clf.predict_accept_prob(crit_security)
    p_low = clf.predict_accept_prob(low_style)

    assert p_crit > p_low
    ranked = clf.rank_and_filter([low_style, crit_security], min_prob=0.3)
    assert ranked[0] == crit_security

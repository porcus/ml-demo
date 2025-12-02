from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from app.models.applications import Application, DecisionOutcome
from app.models.rules import RuleCandidate
from app.models.decisions import RuleEvaluation
from .rule_utils import (
    find_best_univariate_threshold,
    score_from_confidence,
)

RULE_TYPE_ID = "many_30d_lates"


def mine_many_30d_lates_rule(
    manual_apps: List[Application],
) -> Optional[RuleCandidate]:
    """
    Mine a rule of the form:
      IF num_30d_late_last_12m >= T THEN decline
    where T is chosen from a small candidate set based on support & confidence.
    """
    target_decision: DecisionOutcome = "decline"

    best = find_best_univariate_threshold(
        manual_apps,
        feature_getter=lambda a: a.num_30d_late_last_12m,
        candidate_thresholds=[1, 2, 3, 4, 5],
        target_decision=target_decision,
        direction="ge",
    )

    if best is None:
        return None

    thr_30d, support, conf, decline_codes = best
    base_score = score_from_confidence(conf, target_decision)

    rule = RuleCandidate(
        rule_instance_id=str(uuid4()),
        rule_type_id=RULE_TYPE_ID,
        name=f"{thr_30d}+ recent 30-day delinquencies",
        expression=f"num_30d_late_last_12m >= {thr_30d}",
        description=(
            "Historically associated with declines when applicants have "
            f"{thr_30d} or more 30-day late payments in the last 12 months."
        ),
        condition=None,
        target_decision_hint=target_decision,
        suggested_base_score=base_score,
        suggested_weight=1.0,
        suggested_hard_decline=conf >= 0.98,
        support_count=support,
        confidence=conf,
        lift=None,
        aligned_decline_reason_codes=decline_codes,
        llm_explanation=None,
    )

    return rule



def evaluate_many_30d_lates_rule(
    rule: RuleCandidate,
    app: Application,
    weight_override: float,
) -> RuleEvaluation:
    """
    Evaluate this rule for a single application.

    - Parses the threshold from rule.expression (e.g. ">= 3")
    - Checks if num_30d_late_last_12m >= threshold
    - If fired, applies base_score * weight_override as rule_score
    """
    # Very small, shape-specific parser for "num_30d_late_last_12m >= X"
    try:
        parts = rule.expression.split(">=")
        threshold_str = parts[1].strip()
        threshold = int(threshold_str)
    except Exception:
        # If parsing fails for any reason, treat as non-firing rule
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details="Failed to parse threshold from expression.",
            decline_reason_codes=[],
        )

    fired = app.num_30d_late_last_12m >= threshold

    if not fired:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details=f"num_30d_late_last_12m={app.num_30d_late_last_12m} < {threshold}",
            decline_reason_codes=[],
        )

    base_score = rule.suggested_base_score
    rule_score = base_score * weight_override

    decline_codes: list[str] = []
    if rule_score < 0:
        decline_codes = rule.aligned_decline_reason_codes

    return RuleEvaluation(
        rule_id=rule.rule_instance_id,
        rule_name=rule.name,
        fired=True,
        rule_score=rule_score,
        match_details=(
            f"num_30d_late_last_12m={app.num_30d_late_last_12m} >= {threshold}"
        ),
        decline_reason_codes=decline_codes,
    )
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from app.models.applications import Application, DecisionOutcome
from app.models.rules import RuleCandidate
from app.models.decisions import RuleEvaluation
from .rule_utils import (
    find_best_score_dti_combo,
    score_from_confidence,
)

RULE_TYPE_ID = "high_score_low_dti"


def mine_high_score_low_dti_rule(
    manual_apps: List[Application],
) -> Optional[RuleCandidate]:
    """
    Mine a rule of the form:
      IF credit_score >= S AND dti_ratio <= D THEN approve
    where (S, D) are chosen from candidate grids based on support & confidence.
    """
    target_decision: DecisionOutcome = "approve"

    score_thresholds = [720, 740, 760, 780, 800, 820, 840]
    dti_thresholds = [0.25, 0.30, 0.35, 0.40]

    best = find_best_score_dti_combo(
        manual_apps,
        score_thresholds=score_thresholds,
        dti_thresholds=dti_thresholds,
        target_decision=target_decision,
    )

    if best is None:
        return None

    best_score_thr, best_dti_thr, support, conf = best
    base_score = score_from_confidence(conf, target_decision)

    rule = RuleCandidate(
        rule_instance_id=str(uuid4()),
        rule_type_id=RULE_TYPE_ID,
        name=f"Score >= {best_score_thr} & DTI <= {best_dti_thr:.2f}",
        expression=(
            f"credit_score >= {best_score_thr} and dti_ratio <= {best_dti_thr:.2f}"
        ),
        description=(
            "Historically associated with approvals when applicants have "
            f"a credit score at or above {best_score_thr} and a debt-to-income ratio "
            f"at or below {best_dti_thr:.2f}."
        ),
        condition=None,
        target_decision_hint=target_decision,
        suggested_base_score=base_score,
        suggested_weight=1.0,
        suggested_hard_decline=False,
        support_count=support,
        confidence=conf,
        lift=None,
        aligned_decline_reason_codes=[],
        llm_explanation=None,
    )

    return rule


def evaluate_high_score_low_dti_rule(
    rule: RuleCandidate,
    app: Application,
    weight_override: float,
) -> RuleEvaluation:
    """
    Evaluate this rule for a single application.

    Parses an expression like:
      "credit_score >= 820 and dti_ratio <= 0.35"
    """
    try:
        # crude but effective parser for this specific shape
        expr = rule.expression.lower()
        parts = expr.split("and")
        score_part = parts[0].strip()   # "credit_score >= 820"
        dti_part = parts[1].strip()     # "dti_ratio <= 0.35"

        score_thr_str = score_part.split(">=")[1].strip()
        dti_thr_str = dti_part.split("<=")[1].strip()

        score_thr = int(score_thr_str)
        dti_thr = float(dti_thr_str)
    except Exception:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details="Failed to parse score/DTI thresholds from expression.",
            decline_reason_codes=[],
        )

    fired = (app.credit_score >= score_thr) and (app.dti_ratio <= dti_thr)

    if not fired:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details=(
                f"credit_score={app.credit_score} < {score_thr} "
                f"or dti_ratio={app.dti_ratio:.2f} > {dti_thr:.2f}"
            ),
            decline_reason_codes=[],
        )

    base_score = rule.suggested_base_score
    rule_score = base_score * weight_override

    # This is an approval-oriented rule, so typically no decline reasons.
    decline_codes: list[str] = []

    return RuleEvaluation(
        rule_id=rule.rule_instance_id,
        rule_name=rule.name,
        fired=True,
        rule_score=rule_score,
        match_details=(
            f"credit_score={app.credit_score} >= {score_thr} and "
            f"dti_ratio={app.dti_ratio:.2f} <= {dti_thr:.2f}"
        ),
        decline_reason_codes=decline_codes,
    )
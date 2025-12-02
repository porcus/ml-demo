from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from app.models.applications import Application, DecisionOutcome
from app.models.rules import RuleCandidate
from app.models.decisions import RuleEvaluation
from .rule_utils import score_from_confidence

RULE_TYPE_ID = "low_score_high_dti"

MIN_SUPPORT = 10
MIN_CONFIDENCE = 0.7


def mine_low_score_high_dti_rule(
    manual_apps: List[Application],
) -> Optional[RuleCandidate]:
    """
    Mine a rule of the form:
      IF credit_score <= S AND dti_ratio >= D THEN decline
    choosing (S, D) from small grids based on support & confidence.
    """
    target_decision: DecisionOutcome = "decline"

    score_thresholds = [580, 600, 620, 640]
    dti_thresholds = [0.40, 0.45, 0.50, 0.55]

    manual_only = [app for app in manual_apps if app.decision_source == "manual"]

    best_score_thr: Optional[int] = None
    best_dti_thr: Optional[float] = None
    best_support = 0
    best_conf = 0.0

    for s_thr in score_thresholds:
        for d_thr in dti_thresholds:
            matched = [
                app
                for app in manual_only
                if app.credit_score <= s_thr and app.dti_ratio >= d_thr
            ]
            support = len(matched)
            if support < MIN_SUPPORT:
                continue

            declines = [
                app for app in matched
                if app.final_decision == target_decision
            ]
            if not matched:
                continue

            conf = len(declines) / support

            if conf > best_conf or (conf == best_conf and support > best_support):
                best_conf = conf
                best_support = support
                best_score_thr = s_thr
                best_dti_thr = d_thr

    if best_score_thr is None or best_dti_thr is None or best_conf < MIN_CONFIDENCE:
        return None

    base_score = score_from_confidence(best_conf, target_decision)

    rule = RuleCandidate(
        rule_instance_id=str(uuid4()),
        rule_type_id=RULE_TYPE_ID,
        name=f"Score <= {best_score_thr} & DTI >= {best_dti_thr:.2f} → decline",
        expression=(
            f"credit_score <= {best_score_thr} and dti_ratio >= {best_dti_thr:.2f}"
        ),
        description=(
            "Historically associated with declines when applicants have a low credit "
            f"score (<= {best_score_thr}) and a high debt-to-income ratio "
            f"(>= {best_dti_thr:.2f})."
        ),
        condition=None,
        target_decision_hint=target_decision,
        suggested_base_score=base_score,
        suggested_weight=1.0,
        suggested_hard_decline=best_conf >= 0.95,
        support_count=best_support,
        confidence=best_conf,
        lift=None,
        aligned_decline_reason_codes=["LOW_SCORE", "HIGH_DTI"],
        llm_explanation=None,
    )

    return rule


def evaluate_low_score_high_dti_rule(
    rule: RuleCandidate,
    app: Application,
    weight_override: float,
) -> RuleEvaluation:
    """
    Evaluate this rule for a single application.

    Parses an expression like:
      "credit_score <= 620 and dti_ratio >= 0.50"
    """
    try:
        expr = rule.expression.lower()
        parts = expr.split("and")
        score_part = parts[0].strip()  # "credit_score <= 620"
        dti_part = parts[1].strip()    # "dti_ratio >= 0.50"

        score_thr_str = score_part.split("<=")[1].strip()
        dti_thr_str = dti_part.split(">=")[1].strip()

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

    fired = (app.credit_score <= score_thr) and (app.dti_ratio >= dti_thr)

    if not fired:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details=(
                f"credit_score={app.credit_score} > {score_thr} "
                f"or dti_ratio={app.dti_ratio:.2f} < {dti_thr:.2f}"
            ),
            decline_reason_codes=[],
        )

    base_score = rule.suggested_base_score
    rule_score = base_score * weight_override

    decline_codes: list[str] = []
    if rule_score < 0:
        decline_codes = ["LOW_SCORE", "HIGH_DTI"]

    return RuleEvaluation(
        rule_id=rule.rule_instance_id,
        rule_name=rule.name,
        fired=True,
        rule_score=rule_score,
        match_details=(
            f"credit_score={app.credit_score} <= {score_thr} and "
            f"dti_ratio={app.dti_ratio:.2f} >= {dti_thr:.2f}"
        ),
        decline_reason_codes=decline_codes,
    )

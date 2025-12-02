from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from app.models.applications import Application, DecisionOutcome
from app.models.rules import RuleCandidate
from app.models.decisions import RuleEvaluation
from .rule_utils import score_from_confidence

RULE_TYPE_ID = "thin_file_few_tradelines"

MIN_SUPPORT = 10
MIN_CONFIDENCE = 0.6  # maybe a bit looser; thin-file behavior can be noisier


def mine_thin_file_few_tradelines_rule(
    manual_apps: List[Application],
) -> Optional[RuleCandidate]:
    """
    Mine a rule of the form:
      IF num_open_tradelines <= N AND credit_history_length_years <= Y THEN decline
    """

    target_decision: DecisionOutcome = "decline"

    tradeline_thresholds = [0, 1, 2, 3]
    history_thresholds = [1, 2, 3]  # years

    manual_only = [app for app in manual_apps if app.decision_source == "manual"]

    best_n: Optional[int] = None
    best_y: Optional[float] = None
    best_support = 0
    best_conf = 0.0

    for n_thr in tradeline_thresholds:
        for y_thr in history_thresholds:
            matched = [
                app
                for app in manual_only
                if (
                    app.num_open_tradelines <= n_thr
                    and app.credit_history_length_years <= y_thr
                )
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
                best_n = n_thr
                best_y = y_thr

    if best_n is None or best_y is None or best_conf < MIN_CONFIDENCE:
        return None

    base_score = score_from_confidence(best_conf, target_decision)

    rule = RuleCandidate(
        rule_instance_id=str(uuid4()),
        rule_type_id=RULE_TYPE_ID,
        name=(
            f"Thin file: <= {best_n} tradelines & history <= {best_y} years → decline"
        ),
        expression=(
            f"num_open_tradelines <= {best_n} and "
            f"credit_history_length_years <= {best_y}"
        ),
        description=(
            "Historically associated with declines when applicants have very few "
            f"open tradelines (<= {best_n}) and a short credit history "
            f"(<= {best_y} years), indicating a thin file."
        ),
        condition=None,
        target_decision_hint=target_decision,
        suggested_base_score=base_score,
        suggested_weight=1.0,
        suggested_hard_decline=False,  # often this is more of a 'risk signal' than a hard decline
        support_count=best_support,
        confidence=best_conf,
        lift=None,
        aligned_decline_reason_codes=["INSUFFICIENT_CREDIT_HISTORY"],
        llm_explanation=None,
    )

    return rule


def evaluate_thin_file_few_tradelines_rule(
    rule: RuleCandidate,
    app: Application,
    weight_override: float,
) -> RuleEvaluation:
    """
    Evaluate this rule for a single application.

    Parses an expression like:
      "num_open_tradelines <= 2 and credit_history_length_years <= 2"
    """
    try:
        expr = rule.expression.lower()
        parts = [p.strip() for p in expr.split("and")]

        tradeline_part = parts[0]  # "num_open_tradelines <= 2"
        history_part = parts[1]    # "credit_history_length_years <= 2"

        n_thr_str = tradeline_part.split("<=")[1].strip()
        y_thr_str = history_part.split("<=")[1].strip()

        n_thr = int(n_thr_str)
        y_thr = float(y_thr_str)
    except Exception:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details="Failed to parse tradeline/history thresholds.",
            decline_reason_codes=[],
        )

    fired = (
        app.num_open_tradelines <= n_thr
        and app.credit_history_length_years <= y_thr
    )

    if not fired:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details=(
                f"num_open_tradelines={app.num_open_tradelines} > {n_thr} "
                f"or credit_history_length_years={app.credit_history_length_years:.1f} > {y_thr}"
            ),
            decline_reason_codes=[],
        )

    base_score = rule.suggested_base_score
    rule_score = base_score * weight_override

    decline_codes: list[str] = []
    if rule_score < 0:
        decline_codes = ["INSUFFICIENT_CREDIT_HISTORY"]

    return RuleEvaluation(
        rule_id=rule.rule_instance_id,
        rule_name=rule.name,
        fired=True,
        rule_score=rule_score,
        match_details=(
            f"num_open_tradelines={app.num_open_tradelines} <= {n_thr}, "
            f"credit_history_length_years={app.credit_history_length_years:.1f} <= {y_thr}"
        ),
        decline_reason_codes=decline_codes,
    )

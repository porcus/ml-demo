from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from app.models.applications import Application, DecisionOutcome
from app.models.rules import RuleCandidate
from app.models.decisions import RuleEvaluation
from .rule_utils import score_from_confidence

RULE_TYPE_ID = "long_history_clean_file"

MIN_SUPPORT = 10
MIN_CONFIDENCE = 0.7


def mine_long_history_clean_file_rule(
    manual_apps: List[Application],
) -> Optional[RuleCandidate]:
    """
    Mine a rule of the form:
      IF credit_history_length_years >= Y
         AND no 60d/90d lates
         AND no recent bankruptcy/foreclosure
      THEN approve
    """

    target_decision: DecisionOutcome = "approve"
    history_thresholds = [5, 7, 10, 12]  # in years; tune as desired

    manual_only = [app for app in manual_apps if app.decision_source == "manual"]

    best_thr: Optional[float] = None
    best_support = 0
    best_conf = 0.0

    for years_thr in history_thresholds:
        matched = [
            app
            for app in manual_only
            if (
                app.credit_history_length_years >= years_thr
                and app.num_60d_late_last_24m == 0
                and app.num_90d_late_last_24m == 0
                and not app.bankruptcy_last_7y_flag
                and not app.foreclosure_last_7y_flag
            )
        ]
        support = len(matched)
        if support < MIN_SUPPORT:
            continue

        approves = [
            app for app in matched
            if app.final_decision == target_decision
        ]
        if not matched:
            continue

        conf = len(approves) / support

        if conf > best_conf or (conf == best_conf and support > best_support):
            best_conf = conf
            best_support = support
            best_thr = years_thr

    if best_thr is None or best_conf < MIN_CONFIDENCE:
        return None

    base_score = score_from_confidence(best_conf, target_decision)

    rule = RuleCandidate(
        rule_instance_id=str(uuid4()),
        rule_type_id=RULE_TYPE_ID,
        name=(
            f"History >= {best_thr} years, clean file "
            "→ approve"
        ),
        # We encode only the history threshold in the expression; other conditions
        # are fixed in the evaluator.
        expression=f"credit_history_length_years >= {best_thr}",
        description=(
            "Historically associated with approvals when applicants have a sufficiently "
            f"long credit history (>= {best_thr} years) with no recent 60/90-day "
            "delinquencies and no recent bankruptcy or foreclosure."
        ),
        condition=None,
        target_decision_hint=target_decision,
        suggested_base_score=base_score,
        suggested_weight=1.0,
        suggested_hard_decline=False,
        support_count=best_support,
        confidence=best_conf,
        lift=None,
        aligned_decline_reason_codes=[],
        llm_explanation=None,
    )

    return rule


def evaluate_long_history_clean_file_rule(
    rule: RuleCandidate,
    app: Application,
    weight_override: float,
) -> RuleEvaluation:
    """
    Evaluate this rule for a single application.

    Parses an expression like:
      "credit_history_length_years >= 7"
    and applies additional fixed conditions.
    """
    try:
        expr = rule.expression.lower()
        lhs, rhs = expr.split(">=")
        thr_str = rhs.strip()
        years_thr = float(thr_str)
    except Exception:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details="Failed to parse credit history threshold from expression.",
            decline_reason_codes=[],
        )

    fired = (
        app.credit_history_length_years >= years_thr
        and app.num_60d_late_last_24m == 0
        and app.num_90d_late_last_24m == 0
        and not app.bankruptcy_last_7y_flag
        and not app.foreclosure_last_7y_flag
    )

    if not fired:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details=(
                f"credit_history_length_years={app.credit_history_length_years:.1f} < {years_thr} "
                f"or has 60/90d lates or bankruptcy/foreclosure."
            ),
            decline_reason_codes=[],
        )

    base_score = rule.suggested_base_score
    rule_score = base_score * weight_override

    return RuleEvaluation(
        rule_id=rule.rule_instance_id,
        rule_name=rule.name,
        fired=True,
        rule_score=rule_score,
        match_details=(
            f"credit_history_length_years={app.credit_history_length_years:.1f} >= {years_thr}, "
            "no 60/90d lates, and no recent bankruptcy/foreclosure."
        ),
        decline_reason_codes=[],
    )

from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from app.models.applications import Application, DecisionOutcome
from app.models.rules import RuleCandidate
from app.models.decisions import RuleEvaluation
from .rule_utils import score_from_confidence

RULE_TYPE_ID = "high_utilization_many_revolving"

MIN_SUPPORT = 10
MIN_CONFIDENCE = 0.7


def mine_high_utilization_many_revolving_rule(
    manual_apps: List[Application],
) -> Optional[RuleCandidate]:
    """
    Mine a rule of the form:
      IF revolving_utilization_pct >= U AND num_revolving_accounts >= N THEN decline

    Assumes revolving_utilization_pct is in [0, 1]. If you're using 0–100, multiply
    utilization thresholds by 100.
    """
    target_decision: DecisionOutcome = "decline"

    utilization_thresholds = [0.50, 0.60, 0.70, 0.80]  # 50%+ util, etc.
    revolving_count_thresholds = [3, 4, 5, 6]

    manual_only = [app for app in manual_apps if app.decision_source == "manual"]

    best_u: Optional[float] = None
    best_n: Optional[int] = None
    best_support = 0
    best_conf = 0.0

    for u_thr in utilization_thresholds:
        for n_thr in revolving_count_thresholds:
            matched = [
                app
                for app in manual_only
                if (
                    app.revolving_utilization_pct >= u_thr
                    and app.num_revolving_accounts >= n_thr
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
                best_u = u_thr
                best_n = n_thr

    if best_u is None or best_n is None or best_conf < MIN_CONFIDENCE:
        return None

    base_score = score_from_confidence(best_conf, target_decision)

    rule = RuleCandidate(
        rule_instance_id=str(uuid4()),
        rule_type_id=RULE_TYPE_ID,
        name=(
            f"Utilization >= {best_u:.2f} & "
            f"{best_n}+ revolving accounts → decline"
        ),
        expression=(
            f"revolving_utilization_pct >= {best_u:.2f} and "
            f"num_revolving_accounts >= {best_n}"
        ),
        description=(
            "Historically associated with declines when applicants have high "
            f"revolving utilization (>= {best_u:.2f}) and at least {best_n} "
            "revolving accounts, indicating elevated revolving debt burden."
        ),
        condition=None,
        target_decision_hint=target_decision,
        suggested_base_score=base_score,
        suggested_weight=1.0,
        suggested_hard_decline=best_conf >= 0.95,
        support_count=best_support,
        confidence=best_conf,
        lift=None,
        aligned_decline_reason_codes=["HIGH_REVOLVING_UTILIZATION"],
        llm_explanation=None,
    )

    return rule


def evaluate_high_utilization_many_revolving_rule(
    rule: RuleCandidate,
    app: Application,
    weight_override: float,
) -> RuleEvaluation:
    """
    Evaluate this rule for a single application.

    Parses an expression like:
      "revolving_utilization_pct >= 0.70 and num_revolving_accounts >= 4"
    """
    try:
        expr = rule.expression.lower()
        parts = expr.split("and")
        util_part = parts[0].strip()   # "revolving_utilization_pct >= 0.70"
        count_part = parts[1].strip()  # "num_revolving_accounts >= 4"

        util_thr_str = util_part.split(">=")[1].strip()
        count_thr_str = count_part.split(">=")[1].strip()

        util_thr = float(util_thr_str)
        count_thr = int(count_thr_str)
    except Exception:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details="Failed to parse utilization / revolving count thresholds.",
            decline_reason_codes=[],
        )

    fired = (
        app.revolving_utilization_pct >= util_thr
        and app.num_revolving_accounts >= count_thr
    )

    if not fired:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details=(
                f"revolving_utilization_pct={app.revolving_utilization_pct:.2f} < {util_thr:.2f} "
                f"or num_revolving_accounts={app.num_revolving_accounts} < {count_thr}"
            ),
            decline_reason_codes=[],
        )

    base_score = rule.suggested_base_score
    rule_score = base_score * weight_override

    decline_codes: list[str] = []
    if rule_score < 0:
        decline_codes = ["HIGH_REVOLVING_UTILIZATION"]

    return RuleEvaluation(
        rule_id=rule.rule_instance_id,
        rule_name=rule.name,
        fired=True,
        rule_score=rule_score,
        match_details=(
            f"revolving_utilization_pct={app.revolving_utilization_pct:.2f} >= {util_thr:.2f} "
            f"and num_revolving_accounts={app.num_revolving_accounts} >= {count_thr}"
        ),
        decline_reason_codes=decline_codes,
    )

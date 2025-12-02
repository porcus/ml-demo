from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from app.models.applications import Application, DecisionOutcome
from app.models.rules import RuleCandidate
from app.models.decisions import RuleEvaluation
from .rule_utils import score_from_confidence

RULE_TYPE_ID = "low_utilization_moderate_revolving"

MIN_SUPPORT = 10
MIN_CONFIDENCE = 0.7


def mine_low_utilization_moderate_revolving_rule(
    manual_apps: List[Application],
) -> Optional[RuleCandidate]:
    """
    Mine a rule of the form:
      IF revolving_utilization_pct <= U
         AND num_revolving_accounts BETWEEN [N_min, N_max]
      THEN approve
    """
    target_decision: DecisionOutcome = "approve"

    utilization_thresholds = [0.20, 0.25, 0.30, 0.35]  # 20–35% util
    # (min_count, max_count) ranges for "moderate" number of revolving accounts
    revolving_ranges = [(2, 5), (3, 6), (4, 8)]

    manual_only = [app for app in manual_apps if app.decision_source == "manual"]

    best_u: Optional[float] = None
    best_min: Optional[int] = None
    best_max: Optional[int] = None
    best_support = 0
    best_conf = 0.0

    for u_thr in utilization_thresholds:
        for (n_min, n_max) in revolving_ranges:
            matched = [
                app
                for app in manual_only
                if (
                    app.revolving_utilization_pct <= u_thr
                    and app.num_revolving_accounts >= n_min
                    and app.num_revolving_accounts <= n_max
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
                best_u = u_thr
                best_min = n_min
                best_max = n_max

    if (
        best_u is None
        or best_min is None
        or best_max is None
        or best_conf < MIN_CONFIDENCE
    ):
        return None

    base_score = score_from_confidence(best_conf, target_decision)

    rule = RuleCandidate(
        rule_instance_id=str(uuid4()),
        rule_type_id=RULE_TYPE_ID,
        name=(
            f"Utilization <= {best_u:.2f}, "
            f"{best_min}-{best_max} revolving accounts → approve"
        ),
        expression=(
            f"revolving_utilization_pct <= {best_u:.2f} and "
            f"num_revolving_accounts >= {best_min} and "
            f"num_revolving_accounts <= {best_max}"
        ),
        description=(
            "Historically associated with approvals when applicants have a moderate "
            f"number of revolving accounts ({best_min}–{best_max}) and relatively "
            f"low utilization (<= {best_u:.2f}), suggesting responsible credit usage."
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


def evaluate_low_utilization_moderate_revolving_rule(
    rule: RuleCandidate,
    app: Application,
    weight_override: float,
) -> RuleEvaluation:
    """
    Evaluate this rule for a single application.

    Parses an expression like:
      "revolving_utilization_pct <= 0.30 and num_revolving_accounts >= 3 and num_revolving_accounts <= 6"
    """
    try:
        expr = rule.expression.lower()
        # naive parse: split on "and"
        parts = [p.strip() for p in expr.split("and")]

        util_part = parts[0]   # "revolving_utilization_pct <= 0.30"
        min_part = parts[1]    # "num_revolving_accounts >= 3"
        max_part = parts[2]    # "num_revolving_accounts <= 6"

        util_thr_str = util_part.split("<=")[1].strip()
        min_thr_str = min_part.split(">=")[1].strip()
        max_thr_str = max_part.split("<=")[1].strip()

        util_thr = float(util_thr_str)
        min_thr = int(min_thr_str)
        max_thr = int(max_thr_str)
    except Exception:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details="Failed to parse utilization / revolving count range.",
            decline_reason_codes=[],
        )

    fired = (
        app.revolving_utilization_pct <= util_thr
        and app.num_revolving_accounts >= min_thr
        and app.num_revolving_accounts <= max_thr
    )

    if not fired:
        return RuleEvaluation(
            rule_id=rule.rule_instance_id,
            rule_name=rule.name,
            fired=False,
            rule_score=0.0,
            match_details=(
                f"revolving_utilization_pct={app.revolving_utilization_pct:.2f} > {util_thr:.2f} "
                f"or num_revolving_accounts={app.num_revolving_accounts} not in [{min_thr}, {max_thr}]"
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
            f"revolving_utilization_pct={app.revolving_utilization_pct:.2f} <= {util_thr:.2f}, "
            f"num_revolving_accounts={app.num_revolving_accounts} in [{min_thr}, {max_thr}]"
        ),
        decline_reason_codes=[],
    )

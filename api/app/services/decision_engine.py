from __future__ import annotations

from typing import Dict, List

from app.models.applications import Application
from app.models.profiles import DecisionProfile, ProfileRuleConfig
from app.models.decisions import (
    RuleEvaluation,
    ProfileDecisionResult,
    ApplicationDecisionResult,
    ProfileDecision,
)

from app.services.rule_mining.rule_many_30d_lates import (
    RULE_TYPE_ID as MANY_30D_TYPE_ID,
    evaluate_many_30d_lates_rule,
)
from app.services.rule_mining.rule_high_score_low_dti import (
    RULE_TYPE_ID as HIGH_SCORE_DTI_TYPE_ID,
    evaluate_high_score_low_dti_rule,
)
from app.services.rule_mining.rule_high_utilization_many_revolving import (
    RULE_TYPE_ID as HIGH_UTILIZATION_TYPE_ID,
    evaluate_high_utilization_many_revolving_rule,
)
from app.services.rule_mining.rule_long_history_clean_file import (
    RULE_TYPE_ID as LONG_HISTORY_TYPE_ID,
    evaluate_long_history_clean_file_rule,
)
from app.services.rule_mining.rule_low_score_high_dti import (
    RULE_TYPE_ID as LOW_SCORE_HIGH_DTI_TYPE_ID,
    evaluate_low_score_high_dti_rule,
)
from app.services.rule_mining.rule_low_utilization_moderate_revolving import (
    RULE_TYPE_ID as LOW_UTILIZATION_TYPE_ID,
    evaluate_low_utilization_moderate_revolving_rule,
)
from app.services.rule_mining.rule_thin_file_few_tradelines import (
    RULE_TYPE_ID as THIN_FILE_TYPE_ID,
    evaluate_thin_file_few_tradelines_rule,
)



# Map rule_type_id -> evaluator function
# Each evaluator: (rule: RuleCandidate, app: Application, weight_override: float) -> RuleEvaluation
RULE_EVALUATORS = {
    MANY_30D_TYPE_ID: evaluate_many_30d_lates_rule,
    HIGH_SCORE_DTI_TYPE_ID: evaluate_high_score_low_dti_rule,
    HIGH_UTILIZATION_TYPE_ID: evaluate_high_utilization_many_revolving_rule,
    LONG_HISTORY_TYPE_ID: evaluate_long_history_clean_file_rule,
    LOW_SCORE_HIGH_DTI_TYPE_ID: evaluate_low_score_high_dti_rule,
    LOW_UTILIZATION_TYPE_ID: evaluate_low_utilization_moderate_revolving_rule,
    THIN_FILE_TYPE_ID: evaluate_thin_file_few_tradelines_rule,
}


def _evaluate_profile_on_application(
    app: Application,
    profile: DecisionProfile,
) -> ProfileDecisionResult:
    """
    Apply a DecisionProfile to a single Application.
    """
    rule_evals: List[RuleEvaluation] = []
    hard_decline_triggered = False

    for prc in profile.rules:
        if not prc.active:
            continue

        rule = prc.rule
        evaluator = RULE_EVALUATORS.get(rule.rule_type_id)
        
        if evaluator is None:
            # No evaluator for this rule id; safe no-op
            rule_evals.append(
                RuleEvaluation(
                    rule_id=rule.rule_instance_id,
                    rule_name=rule.name,
                    fired=False,
                    rule_score=0.0,
                    match_details=f"No evaluator registered for rule_type_id={rule.rule_type_id}.",
                    decline_reason_codes=[],
                )
            )
            continue

        # Evaluate the rule
        re = evaluator(rule, app, prc.weight_override)
        rule_evals.append(re)

        # Track hard-decline
        if prc.hard_decline and re.fired:
            hard_decline_triggered = True

    total_score = sum(re.rule_score for re in rule_evals)

    # Aggregate decline reasons from any negative rules that fired
    profile_decline_codes: set[str] = set()
    for re in rule_evals:
        for code in re.decline_reason_codes:
            profile_decline_codes.add(code)

    # Determine profile-level decision
    if hard_decline_triggered:
        decision: ProfileDecision = "decline"
    else:
        # Simple scheme:
        # - total_score >= threshold => approve
        # - threshold - 20 <= total_score < threshold => refer
        # - else decline
        if total_score >= profile.approval_threshold:
            decision = "approve"
        elif total_score >= profile.approval_threshold - 20:
            decision = "refer"
        else:
            decision = "decline"

    return ProfileDecisionResult(
        profile_id=profile.id or "",
        profile_name=profile.name,
        total_score=total_score,
        decision=decision,
        hard_decline_triggered=hard_decline_triggered,
        rule_evaluations=rule_evals,
        decline_reason_codes=sorted(profile_decline_codes),
    )


def _aggregate_final_decision(
    profile_results: List[ProfileDecisionResult],
) -> tuple[ProfileDecision, bool, List[str]]:
    """
    Aggregate decisions across profiles for a single application.

    For now:
      - If ANY profile approves and NONE decline hard => "approve"
      - Else if ALL profiles decline => "decline"
      - Else => "refer"
    """
    if not profile_results:
        return "refer", True, []

    any_approve = any(pr.decision == "approve" for pr in profile_results)
    any_decline = any(pr.decision == "decline" for pr in profile_results)

    # Combine decline reason codes from all profiles
    all_decline_codes: set[str] = set()
    for pr in profile_results:
        for code in pr.decline_reason_codes:
            all_decline_codes.add(code)

    if any_approve and not any_decline:
        final_decision: ProfileDecision = "approve"
    elif any_decline and not any_approve:
        final_decision = "decline"
    else:
        final_decision = "refer"

    needs_manual_review = final_decision == "refer"

    return final_decision, needs_manual_review, sorted(all_decline_codes)


def run_decision_engine(
    applications: List[Application],
    profiles: List[DecisionProfile],
) -> List[ApplicationDecisionResult]:
    """
    Evaluate one or more DecisionProfiles against a set of Applications.
    """
    results: List[ApplicationDecisionResult] = []

    for app in applications:
        # Evaluate each profile on this application
        profile_results: List[ProfileDecisionResult] = [
            _evaluate_profile_on_application(app, profile)
            for profile in profiles
        ]

        final_system_decision, needs_manual_review, agg_decline_codes = _aggregate_final_decision(
            profile_results
        )

        result = ApplicationDecisionResult(
            application_id=app.application_id,
            manual_decision_source=app.decision_source,
            manual_final_decision=app.final_decision,
            manual_decline_reasons=app.manual_decline_reasons,
            profile_results=profile_results,
            final_system_decision=final_system_decision,
            needs_manual_review=needs_manual_review,
            aggregated_decline_reason_codes=agg_decline_codes,
        )

        results.append(result)

    return results

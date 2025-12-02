from __future__ import annotations

import os
from typing import List, Optional
from datetime import datetime

from app.models.applications import Application, DecisionOutcome
from app.models.rules import RuleCandidate
from app.models.profiles import DecisionProfile, ProfileRuleConfig
from app.models.rule_miner_models import RuleMinerResponse, RuleMinerSummaryMetrics
from app.services.llm_client import get_lm_client, LMSTUDIO_MODEL

from app.services.rule_mining.rule_many_30d_lates import (
    mine_many_30d_lates_rule,
)
from app.services.rule_mining.rule_high_score_low_dti import (
    mine_high_score_low_dti_rule,
)
from app.services.rule_mining.rule_high_utilization_many_revolving import (
    mine_high_utilization_many_revolving_rule,
)
from app.services.rule_mining.rule_long_history_clean_file import (
    mine_long_history_clean_file_rule,
)
from app.services.rule_mining.rule_low_score_high_dti import (
    mine_low_score_high_dti_rule,
)
from app.services.rule_mining.rule_low_utilization_moderate_revolving import (
    mine_low_utilization_moderate_revolving_rule,
)
from app.services.rule_mining.rule_thin_file_few_tradelines import (
    mine_thin_file_few_tradelines_rule,
)


# -------------------------------------------------------------------

def _explain_rule_with_llm(rule: RuleCandidate) -> str:
    """
    Ask the LLM to explain a candidate rule in plain language for a credit/risk audience.
    """
    # Keep the prompt small and structured
    user_content = f"""
You are an experienced consumer lending risk analyst.

Explain the following candidate decision rule in a concise way (3–5 sentences) using plain language.
Focus on:
- what kind of applicants this rule is about,
- why this rule might lead to an approval or decline,
- and any caveats or things an underwriter should keep in mind.

Rule instance ID: {rule.rule_instance_id}
Rule type ID: {rule.rule_type_id}
Name: {rule.name}
Expression: {rule.expression}
Target decision hint: {rule.target_decision_hint}
Support (number of matching loans): {rule.support_count}
Confidence (fraction of matches with that decision): {rule.confidence:.2f}
Aligned decline reason codes: {", ".join(rule.aligned_decline_reason_codes) or "none"}
    """.strip()

    lm_client = get_lm_client()
    response = lm_client.chat.completions.create(
        model=LMSTUDIO_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a concise, pragmatic credit risk expert. Avoid legal advice; focus on risk reasoning.",
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        max_tokens=300,
        temperature=0.3,
    )

    text = response.choices[0].message.content or ""
    return text.strip()


def _explain_profile_with_llm(
    profile: DecisionProfile,
    rules: List[RuleCandidate],
) -> str:
    """
    Ask the LLM to give a high-level explanation of what this profile is doing overall.
    """
    # Summarize rules for the prompt: id, name, expression, target_decision_hint
    rules_summary_lines = []
    for r in rules:
        rules_summary_lines.append(
            f"- instance={r.rule_instance_id}, type={r.rule_type_id}: "
            f"{r.name} | expr: {r.expression} | target: {r.target_decision_hint}, "
            f"score: {r.suggested_base_score}"
        )
    rules_summary = "\n".join(rules_summary_lines) or "No rules."

    user_content = f"""
You are an experienced consumer lending risk analyst.

A "decision profile" is a collection of decision rules used to score and automatically
approve or decline personal loan applications. Each rule contributes a positive or negative
score; the total score is compared against an approval threshold.

Explain the following decision profile in 4–6 sentences:
- What kind of borrowers this profile is likely to approve or decline,
- The general philosophy of the rules (e.g., conservative vs aggressive),
- Any obvious strengths and weaknesses from a risk perspective.

Profile name: {profile.name}
Description: {profile.description or "None"}
Approval threshold: {profile.approval_threshold}

Rules in the profile:
{rules_summary}
    """.strip()

    lm_client = get_lm_client()
    response = lm_client.chat.completions.create(
        model=LMSTUDIO_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a concise, pragmatic credit risk expert. Avoid legal advice; focus on risk/reward trade-offs.",
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        max_tokens=400,
        temperature=0.3,
    )

    text = response.choices[0].message.content or ""
    return text.strip()


def mine_rules(applications: List[Application]) -> RuleMinerResponse:
    """
    Orchestrates rule mining:
      - Filters to manually-decisioned loans
      - Calls per-rule miners
      - Assembles a candidate DecisionProfile
      - Uses LLM to generate explanations (best-effort)
    """
    manual_apps: List[Application] = [
        a for a in applications if a.decision_source == "manual"
    ]

    if not manual_apps:
        summary = RuleMinerSummaryMetrics(
            num_loans_analyzed=0,
        )
        empty_profile = DecisionProfile(
            id=None,
            name="Empty profile (no manual loans available)",
            description=None,
            approval_threshold=50.0,
            rules=[],
            created_at=None,
            created_by=None,
            source_application_ids=[],
            llm_explanation=None,
        )
        return RuleMinerResponse(
            candidate_profile=empty_profile,
            summary_metrics=summary,
        )

    # ----------------------------------------------------------------
    # Call per-rule miners and collect candidate rule instances
    # ----------------------------------------------------------------
    candidate_rules: List[RuleCandidate] = []

    # # 1) Many 30d lates -> decline
    # rule_30d = mine_many_30d_lates_rule(manual_apps)
    # if rule_30d is not None:
    #     candidate_rules.append(rule_30d)

    # # 2) High score & low DTI -> approve
    # rule_score_dti = mine_high_score_low_dti_rule(manual_apps)
    # if rule_score_dti is not None:
    #     candidate_rules.append(rule_score_dti)

    rule_miners = [ mine_many_30d_lates_rule, mine_high_score_low_dti_rule, mine_high_utilization_many_revolving_rule, mine_long_history_clean_file_rule, mine_low_score_high_dti_rule, mine_low_utilization_moderate_revolving_rule, mine_thin_file_few_tradelines_rule]
    for miner in rule_miners:
        rule = miner(manual_apps)
        if rule is not None:
            candidate_rules.append(rule)


    # TODO: add more rule mining calls here

    # Build ProfileRuleConfig for each candidate rule
    profile_rules: List[ProfileRuleConfig] = [
        ProfileRuleConfig(
            rule=rc,
            weight_override=1.0,
            hard_decline=(
                rc.target_decision_hint == "decline" and rc.suggested_hard_decline
            ),
            active=True,
        )
        for rc in candidate_rules
    ]

    source_app_ids = [a.application_id for a in manual_apps]

    candidate_profile = DecisionProfile(
        id=None,
        name="Auto profile from manual decisions",
        description=(
            "Profile assembled automatically from manually-decisioned loans, "
            "using simple pattern mining on delinquencies and high-score/low-DTI segments."
        ),
        approval_threshold=50.0,  # TBD: make this data-driven later
        rules=profile_rules,
        created_at=datetime.utcnow(),
        created_by=None,
        source_application_ids=source_app_ids,
        llm_explanation=None,
    )

    summary = RuleMinerSummaryMetrics(
        num_loans_analyzed=len(manual_apps),
        num_loans_train=None,
        num_loans_validation=None,
        train_match_rate=None,
        validation_match_rate=None,
        train_auto_decision_rate=None,
        validation_auto_decision_rate=None,
        false_approvals=None,
        false_declines=None,
    )

    # ----------------------------------------------------------------
    # LLM EXPLANATIONS (best-effort)
    # ----------------------------------------------------------------
    if candidate_rules:
        try:
            for rc in candidate_rules:
                try:
                    rc.llm_explanation = _explain_rule_with_llm(rc)
                except Exception:
                    rc.llm_explanation = None

            try:
                candidate_profile.llm_explanation = _explain_profile_with_llm(
                    candidate_profile,
                    candidate_rules,
                )
            except Exception:
                candidate_profile.llm_explanation = None

        except Exception:
            # Never break the deterministic miner due to LLM failures
            pass

    return RuleMinerResponse(
        candidate_profile=candidate_profile,
        summary_metrics=summary,
    )

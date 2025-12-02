from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel

from app.models.applications import (
    DecisionSource,
    DecisionOutcome,
    DeclineReason,
)

class RuleEvaluation(BaseModel):
    rule_id: str
    rule_name: Optional[str] = None

    fired: bool                      # did the condition match?
    rule_score: float                # base_score * weight (0 if not fired)

    # Optional: how strongly it matched (if you go beyond simple booleans later)
    match_details: Optional[str] = None

    # Decline reasons associated with this rule when it contributes negatively
    decline_reason_codes: List[str] = []


ProfileDecision = Literal["approve", "decline", "refer"]


class ProfileDecisionResult(BaseModel):
    profile_id: str
    profile_name: str

    total_score: float
    decision: ProfileDecision
    hard_decline_triggered: bool

    rule_evaluations: List[RuleEvaluation]

    # Aggregate decline reasons for this profile (from fired negative rules)
    decline_reason_codes: List[str] = []


class ApplicationDecisionResult(BaseModel):
    application_id: str

    # Historic manual labels (if present)
    manual_decision_source: Optional[DecisionSource] = None
    manual_final_decision: Optional[DecisionOutcome] = None
    manual_decline_reasons: List[DeclineReason] = []

    # Per-profile decisions
    profile_results: List[ProfileDecisionResult]

    # Aggregated view across selected profiles
    final_system_decision: ProfileDecision  # e.g. your "all approve" vs "none approve" logic
    needs_manual_review: bool               # true when mixed/conflicting

    # Combined decline reasons where system or any profile declined
    aggregated_decline_reason_codes: List[str] = []

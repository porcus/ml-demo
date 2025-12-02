from __future__ import annotations

from typing import List, Optional
from app.models.rules import RuleCandidate
from pydantic import BaseModel
from datetime import datetime

class ProfileRuleConfig(BaseModel):
    # Instead of just rule_id, we embed the entire rule instance
    rule: RuleCandidate

    weight_override: float = 1.0     # multiplies base_score
    hard_decline: bool = False       # if true and this rule fires, profile-level decision = decline
    active: bool = True


class DecisionProfile(BaseModel):
    id: Optional[str] = None         # None for new / candidate profiles; set once saved
    name: str
    description: Optional[str] = None

    approval_threshold: float        # total score required for "approve"

    rules: List[ProfileRuleConfig]

    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    # future: modified_at, modified_by, version, etc.

    # NEW: which application_ids were used to mine/build this profile
    source_application_ids: List[str] = []

    # NEW: LLM explanation of the profile as a whole
    llm_explanation: Optional[str] = None

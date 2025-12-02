from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel
from app.models.applications import DecisionOutcome

class RuleCondition(BaseModel):
    """
    Optional structured representation of a condition.
    You can start with just `expression` in RuleCandidate if you want and add this later.
    """
    field: str            # e.g. "num_30d_late_last_12m"
    operator: str         # e.g. ">=", "<", "between"
    value: float | int | str | List[float | int | str]


class RuleCandidate(BaseModel):
    # NEW: unique per rule instance
    rule_instance_id: str              # e.g. UUID string

    # NEW: identifies the rule shape/template (e.g. "many_30d_lates")
    rule_type_id: str

    name: str                        # human-friendly name
    expression: str                  # e.g. "num_30d_late_last_12m >= 3"
    description: Optional[str] = None

    # Optional structured condition (v2)
    condition: Optional[RuleCondition] = None

    target_decision_hint: Optional[DecisionOutcome] = None  # usually "approve" or "decline"

    # Scoring suggestion from miner
    suggested_base_score: float      # e.g. -80, +60
    suggested_weight: float = 1.0    # default relative weight
    suggested_hard_decline: bool = False

    # Stats from historical data
    support_count: int               # how many loans matched this condition
    confidence: float                # fraction of those loans with the same manual decision (0–1)
    lift: Optional[float] = None     # optional, if you compute it

    aligned_decline_reason_codes: List[str] = []  # from manual_decline_reasons

    llm_explanation: Optional[str] = None         # natural-language explanation/suggestion


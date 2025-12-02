from typing import List, Optional
from pydantic import BaseModel

from app.models.rules import RuleCandidate
from app.models.profiles import DecisionProfile

#---------------------------------------------------
# API request/response models
#---------------------------------------------------

# class RuleMinerRequest(BaseModel):
#     applications: List[Application]


class RuleMinerSummaryMetrics(BaseModel):
    num_loans_analyzed: int

    # If you implement train/validation split later:
    num_loans_train: Optional[int] = None
    num_loans_validation: Optional[int] = None

    # How well the candidate profile matches manual decisions on those sets
    train_match_rate: Optional[float] = None          # 0–1
    validation_match_rate: Optional[float] = None     # 0–1

    train_auto_decision_rate: Optional[float] = None  # fraction of loans profile can auto-decide
    validation_auto_decision_rate: Optional[float] = None

    # Misclassification counts (optional but nice)
    false_approvals: Optional[int] = None
    false_declines: Optional[int] = None


class RuleMinerResponse(BaseModel):
    candidate_profile: DecisionProfile    # suggestion, typically without an id
    summary_metrics: RuleMinerSummaryMetrics
from typing import List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime


DecisionSource = Literal["auto", "manual"]
DecisionOutcome = Literal["approve", "decline"]
PerformanceLabel = Literal["good", "30d_plus_delinquent", "60d_plus_delinquent", "default"]


class DeclineReason(BaseModel):
    code: str                        # e.g. "LOW_SCORE", "HIGH_DTI"
    description: str                 # human-friendly explanation
    ecoa_category: Optional[str] = None  # optional high-level category


class Application(BaseModel):
    # Identity & context
    application_id: str
    application_datetime: datetime
    channel: Literal["online", "branch", "broker", "phone"]
    product_type: Literal["personal", "auto", "small_business"]
    loan_purpose: Literal[
        "debt_consolidation", "home_improvement", "auto_purchase", "education", "other"
    ]
    state: str  # 2-letter code

    # Terms
    loan_amount: float
    loan_term_months: int
    secured_flag: bool
    collateral_type: Optional[Literal["vehicle", "savings", "property", "none"]] = None
    collateral_value: Optional[float] = None
    ltv_ratio: Optional[float] = None  # loan_amount / collateral_value

    prior_relationship_flag: bool

    # Credit profile
    credit_score: int
    credit_history_length_years: float
    num_open_tradelines: int
    num_revolving_accounts: int
    revolving_utilization_pct: float   # 0–1

    num_30d_late_last_12m: int
    num_60d_late_last_24m: int
    num_90d_late_last_24m: int

    bankruptcy_last_7y_flag: bool
    foreclosure_last_7y_flag: bool
    collections_count: int
    chargeoff_count: int
    public_judgment_count: int

    inquiries_last_6m: int

    # Capacity / income
    monthly_gross_income: float
    monthly_debt_payments: float
    dti_ratio: float                   # debt / income (0–1)

    employment_status: Literal["employed_full_time", "employed_part_time", "self_employed", "unemployed", "retired",]
    months_in_job: int
    months_in_industry: Optional[int] = None

    # Decision labels (from historical/manual processing)
    decision_source: DecisionSource     # "manual" for the training set
    final_decision: DecisionOutcome     # approve/decline
    manual_decline_reasons: List[DeclineReason] = []

    # Optional: later for performance analysis
    performance_12m: Optional[PerformanceLabel] = None

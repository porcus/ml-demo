import json
import random
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List

from fastapi import HTTPException

from app.models.applications import Application, DecisionOutcome, DecisionSource, DeclineReason
from app.models.application_generation import GenerateApplicationsRequest
from app.services.llm_client import get_lm_client, LMSTUDIO_MODEL


# --------- PUBLIC ENTRY POINT --------- #

def generate_applications(req: GenerateApplicationsRequest) -> List[Application]:
    try:
        req.validate_counts()
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    if req.generation_strategy == "python":
        return _generate_with_python(req)
    elif req.generation_strategy == "llm":
        return _generate_with_llm(req)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown generation_strategy: {req.generation_strategy}",
        )


# --------- PYTHON GENERATOR --------- #

def _generate_with_python(req: GenerateApplicationsRequest) -> List[Application]:
    if req.seed is not None:
        random.seed(req.seed)

    total = req.total_count
    manual = req.manual_count
    manual_approved = req.manual_approved_count
    manual_declined = manual - manual_approved
    undecisioned = total - manual

    apps: List[Application] = []

    # Generate manual approved apps
    for _ in range(manual_approved):
        apps.append(_make_python_app(decision_source="manual", final_decision="approve"))

    # Manual declined apps
    for _ in range(manual_declined):
        apps.append(_make_python_app(decision_source="manual", final_decision="decline"))

    # Undecisioned: we set decision_source="auto" and final_decision=None
    for _ in range(undecisioned):
        apps.append(_make_python_app(decision_source="auto", final_decision=None))

    # Shuffle so they are not grouped by type
    random.shuffle(apps)
    return apps


def _make_python_app(
    decision_source: DecisionSource,
    final_decision: DecisionOutcome | None,
) -> Application:
    """
    Generate a single Application with plausible values.
    Manual-approved apps will skew toward "good" features.
    Manual-declined apps will skew toward "risky" features.
    Undecisioned apps will be somewhere in the middle.
    """

    now = datetime.utcnow()
    # Random application date within last 90 days
    application_datetime = now - timedelta(days=random.randint(0, 90))

    # Basic categorical choices
    channel = random.choice(["online", "branch", "broker", "phone"])
    product_type = random.choice(["personal", "auto", "small_business"])
    loan_purpose = random.choice(
        ["debt_consolidation", "home_improvement", "auto_purchase", "education", "other"]
    )
    state = random.choice(["CA", "TX", "NY", "FL", "WA", "IL"])

    # We'll adjust ranges based on final_decision for realism
    if final_decision == "approve":
        credit_score = random.randint(680, 840)
        dti_ratio = random.uniform(0.1, 0.45)
        num_30d_late_last_12m = random.randint(0, 1)
        bankruptcy_flag = False
        foreclosure_flag = False
        collections_count = random.choice([0, 0, 1])
    elif final_decision == "decline":
        credit_score = random.randint(520, 700)
        dti_ratio = random.uniform(0.4, 0.9)
        num_30d_late_last_12m = random.randint(1, 6)
        bankruptcy_flag = random.choice([False, True])
        foreclosure_flag = random.choice([False, True])
        collections_count = random.randint(0, 5)
    else:
        # undecisioned / unknown
        credit_score = random.randint(580, 800)
        dti_ratio = random.uniform(0.2, 0.7)
        num_30d_late_last_12m = random.randint(0, 3)
        bankruptcy_flag = random.choice([False, False, True])
        foreclosure_flag = random.choice([False, False, True])
        collections_count = random.randint(0, 3)

    # Income/loan/debt consistent with DTI
    monthly_gross_income = random.randint(3000, 12000)
    monthly_debt_payments = max(
        50,
        int(monthly_gross_income * dti_ratio * random.uniform(0.9, 1.1)),
    )

    # Loan amount based on income, decision, and product
    base_factor = 6 if product_type == "personal" else 10
    if final_decision == "approve":
        loan_amount = int(monthly_gross_income * random.uniform(2, base_factor))
    elif final_decision == "decline":
        loan_amount = int(monthly_gross_income * random.uniform(5, base_factor * 1.5))
    else:
        loan_amount = int(monthly_gross_income * random.uniform(2, base_factor * 1.2))

    # Collateral & LTV for secured loans
    secured_flag = product_type in ["auto"]
    if secured_flag:
        collateral_type = "vehicle"
        collateral_value = int(loan_amount * random.uniform(1.0, 1.4))
        ltv_ratio = loan_amount / collateral_value
    else:
        collateral_type = None
        collateral_value = None
        ltv_ratio = None

    loan_term_months = random.choice([36, 48, 60, 72])

    # Credit file features
    credit_history_length_years = random.randint(1, 30)
    num_open_tradelines = random.randint(2, 15)
    num_revolving_accounts = random.randint(1, 10)
    revolving_utilization_pct = random.uniform(0.05, 0.9)

    num_60d_late_last_24m = random.randint(0, 3 if final_decision == "decline" else 1)
    num_90d_late_last_24m = random.randint(0, 2 if final_decision == "decline" else 0)

    chargeoff_count = random.randint(0, 3 if final_decision == "decline" else 1)
    public_judgment_count = random.randint(0, 2 if final_decision == "decline" else 0)

    inquiries_last_6m = random.randint(0, 6 if final_decision == "decline" else 3)

    # Employment
    employment_status = random.choice(["employed_full_time", "employed_part_time", "self_employed", "unemployed", "retired"])
    months_in_job = random.randint(0, 240)
    months_in_industry = months_in_job + random.randint(0, 120)

    prior_relationship_flag = random.choice([True, False])

    # Decline reasons if declined
    manual_decline_reasons: List[DeclineReason] = []
    if final_decision == "decline":
        reason_codes: List[DeclineReason] = []

        if credit_score < 640:
            reason_codes.append(
                DeclineReason(
                    code="LOW_SCORE",
                    description="Credit score below minimum threshold.",
                    ecoa_category="credit_history",
                )
            )
        if dti_ratio > 0.5:
            reason_codes.append(
                DeclineReason(
                    code="HIGH_DTI",
                    description="Debt-to-income ratio too high.",
                    ecoa_category="capacity",
                )
            )
        if num_30d_late_last_12m >= 3:
            reason_codes.append(
                DeclineReason(
                    code="EXCESSIVE_DELINQUENCY",
                    description="Too many recent late payments.",
                    ecoa_category="credit_history",
                )
            )
        if bankruptcy_flag:
            reason_codes.append(
                DeclineReason(
                    code="RECENT_BANKRUPTCY",
                    description="Recent bankruptcy on credit file.",
                    ecoa_category="public_record",
                )
            )

        # Ensure at least one reason if declined
        if not reason_codes:
            reason_codes.append(
                DeclineReason(
                    code="MANUAL_POLICY",
                    description="Does not meet underwriting criteria.",
                    ecoa_category="other",
                )
            )

        manual_decline_reasons = reason_codes
    else:
        manual_decline_reasons = []

    # Performance indicator (rough guess)
    if final_decision == "approve":
        if credit_score >= 720 and dti_ratio <= 0.4:
            performance_12m = "good"
        elif credit_score >= 650 and dti_ratio <= 0.5:
            performance_12m = "30d_plus_delinquent"
        elif credit_score >= 600 and dti_ratio <= 0.6:
            performance_12m = "60d_plus_delinquent"
        else:
            performance_12m = "default"
    else:
        performance_12m = None

    return Application(
        application_id=str(uuid4()),
        application_datetime=application_datetime.isoformat(),
        channel=channel,
        product_type=product_type,
        loan_purpose=loan_purpose,
        state=state,
        loan_amount=loan_amount,
        loan_term_months=loan_term_months,
        secured_flag=secured_flag,
        collateral_type=collateral_type,
        collateral_value=collateral_value,
        ltv_ratio=ltv_ratio,
        prior_relationship_flag=prior_relationship_flag,
        credit_score=credit_score,
        credit_history_length_years=credit_history_length_years,
        num_open_tradelines=num_open_tradelines,
        num_revolving_accounts=num_revolving_accounts,
        revolving_utilization_pct=revolving_utilization_pct,
        num_30d_late_last_12m=num_30d_late_last_12m,
        num_60d_late_last_24m=num_60d_late_last_24m,
        num_90d_late_last_24m=num_90d_late_last_24m,
        bankruptcy_last_7y_flag=bankruptcy_flag,
        foreclosure_last_7y_flag=foreclosure_flag,
        collections_count=collections_count,
        chargeoff_count=chargeoff_count,
        public_judgment_count=public_judgment_count,
        inquiries_last_6m=inquiries_last_6m,
        monthly_gross_income=monthly_gross_income,
        monthly_debt_payments=monthly_debt_payments,
        dti_ratio=dti_ratio,
        employment_status=employment_status,
        months_in_job=months_in_job,
        months_in_industry=months_in_industry,
        decision_source=decision_source,
        final_decision=final_decision,
        manual_decline_reasons=manual_decline_reasons,
        performance_12m=performance_12m,
    )


# --------- LLM GENERATOR --------- #

def _generate_with_llm(req: GenerateApplicationsRequest) -> List[Application]:
    """
    Use a local LLM (via LM Studio) to generate application records.
    We then parse JSON and map to Application objects.

    NOTE: For robustness, this implementation assumes the LLM returns a JSON array
    of objects that already match our schema reasonably well. You can extend this
    with more validation / repair as needed.
    """
    total = req.total_count
    manual = req.manual_count
    manual_approved = req.manual_approved_count
    manual_declined = manual - manual_approved
    undecisioned = total - manual

    system_prompt = """
You are an assistant that generates synthetic but realistic consumer loan application data.

You must output ONLY valid JSON: a JSON array of objects, with no surrounding text.

Each object represents a single loan application with these fields:

- application_id: a UUID string.
- application_datetime: ISO 8601 datetime string (UTC), within the last 90 days.
- channel: one of ["online", "branch", "broker", "phone"].
- product_type: one of ["personal", "auto", "small_business"].
- loan_purpose: one of ["debt_consolidation", "home_improvement", "auto_purchase", "education", "other"].
- state: a US state code like "CA", "TX", "NY", "FL", "WA", "IL".

- loan_amount: positive integer number of USD.
- loan_term_months: integer from [24, 36, 48, 60, 72].
- secured_flag: boolean.
- collateral_type: one of ["vehicle", "savings", "property", "none"].
- collateral_value: nullable positive integer; if secured_flag is true, this should be >= loan_amount.
- ltv_ratio: nullable float; if secured_flag is true, roughly loan_amount / collateral_value, between 0.5 and 1.4.
- prior_relationship_flag: boolean.

- credit_score: integer in [300, 850].
- credit_history_length_years: integer 0–40.
- num_open_tradelines: integer 0–20.
- num_revolving_accounts: integer 0–20.
- revolving_utilization_pct: float 0.0–1.0 (0–100% utilization).

- num_30d_late_last_12m: integer 0–10.
- num_60d_late_last_24m: integer 0–10.
- num_90d_late_last_24m: integer 0–10.

- bankruptcy_last_7y_flag: boolean.
- foreclosure_last_7y_flag: boolean.
- collections_count: integer 0–10.
- chargeoff_count: integer 0–10.
- public_judgment_count: integer 0–10.

- inquiries_last_6m: integer 0–10.

- monthly_gross_income: integer (e.g. 2000–20000).
- monthly_debt_payments: integer >= 0.
- dti_ratio: float ~ monthly_debt_payments / monthly_gross_income, within about +/-0.15 of that ratio.

- employment_status: one of ["employed_full_time", "employed_part_time", "self_employed", "unemployed", "retired"].
- months_in_job: integer 0–360.
- months_in_industry: integer >= months_in_job.

- decision_source: one of ["manual", "auto"].
- final_decision: one of ["approve", "decline"] or null if undecisioned.
- manual_decline_reasons: array of objects with:
    - code: string
    - description: string
    - ecoa_category: string or null
  For approved or undecisioned applications, this array is usually empty.

- performance_12m: one of ["good", "30d_plus_delinquent", "60d_plus_delinquent", "default"].
  For declined or undecisioned applications, this can be null.

Correlations to follow:
- Higher credit_score, lower dti_ratio, fewer delinquencies, and no bankruptcy -> more likely approved with "good" performance.
- Low scores, high dti_ratio, many delinquencies or bankruptcy/foreclosure -> more likely declined with "30d_plus_delinquent", "60d_plus_delinquent", or "default" performance.
- For declined applications, include at least one decline reason in manual_decline_reasons (e.g., "LOW_SCORE", "HIGH_DTI", "EXCESSIVE_DELINQUENCY", "RECENT_BANKRUPTCY").
    """.strip()

    user_prompt = f"""
Generate exactly {total} application objects.
- {manual} applications must be manually decisioned (decision_source = "manual" and final_decision is either "approve" or "decline").
- Of those manually decisioned, {manual_approved} must be "approve" and {manual_declined} must be "decline".
- The remaining {undecisioned} applications should be undecisioned: decision_source = "auto" and final_decision = null.

Ensure the fields follow the schema and correlations described in the system prompt.
Return ONLY a valid JSON array, nothing else.
    """.strip()

    lm_client = get_lm_client()
    try:
        response = lm_client.chat.completions.create(
            model=LMSTUDIO_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=8192,
            temperature=0.6,
        )
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {ex}",
        )

    content = response.choices[0].message.content or ""
    content = content.strip()

    # Try to parse JSON; if it fails, raise an error (or you could fallback to Python)
    try:
        raw_data = json.loads(content)
    except json.JSONDecodeError as ex:
        raise HTTPException(
            status_code=500,
            detail=f"LLM did not return valid JSON: {ex}",
        )

    if not isinstance(raw_data, list):
        raise HTTPException(
            status_code=500,
            detail="LLM response is not a JSON array.",
        )

    apps: List[Application] = []
    for idx, item in enumerate(raw_data):
        if not isinstance(item, dict):
            continue
        try:
            # Let Pydantic do coercion/validation as a second layer
            app = Application(**item)
            app.application_id=str(uuid4())
        except Exception as ex:
            # Skip invalid entries; you could log ex here
            continue
        apps.append(app)

    if not apps:
        raise HTTPException(
            status_code=500,
            detail="No valid applications could be parsed from LLM output.",
        )

    # If we got more than required, truncate; if fewer, we just return what we have.
    if len(apps) > total:
        apps = apps[:total]

    return apps

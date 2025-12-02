// src/types/loanModels.ts

export type DecisionOutcome = "approve" | "decline";
export type DecisionSource = "auto" | "manual";
export type ProfileDecision = "approve" | "decline" | "refer";

export interface DeclineReason {
  code: string;
  description: string;
  ecoa_category?: string | null;
}

export interface Application {
  application_id: string;
  application_datetime: string; // ISO
  channel: string;
  product_type: string;
  loan_purpose: string;
  state: string;

  loan_amount: number;
  loan_term_months: number;
  secured_flag: boolean;
  collateral_type: string | null;
  collateral_value: number | null;
  ltv_ratio: number | null;
  prior_relationship_flag: boolean;

  credit_score: number;
  credit_history_length_years: number;
  num_open_tradelines: number;
  num_revolving_accounts: number;
  revolving_utilization_pct: number;

  num_30d_late_last_12m: number;
  num_60d_late_last_24m: number;
  num_90d_late_last_24m: number;

  bankruptcy_last_7y_flag: boolean;
  foreclosure_last_7y_flag: boolean;
  collections_count: number;
  chargeoff_count: number;
  public_judgment_count: number;

  inquiries_last_6m: number;

  monthly_gross_income: number;
  monthly_debt_payments: number;
  dti_ratio: number;

  employment_status: string;
  months_in_job: number;
  months_in_industry: number;

  decision_source: DecisionSource;
  final_decision: DecisionOutcome | null; // allow null for undecisioned
  manual_decline_reasons: DeclineReason[];
  performance_12m?: string | null;

  // Client-only metadata (not required on backend)
  sourceType?: "llm" | "python" | "import";
  sourceLabel?: string;
  batchId?: string;
}

export interface RuleCandidate {
  rule_instance_id: string;
  rule_type_id: string;

  name: string;
  expression: string;
  description?: string | null;

  condition?: any | null;

  target_decision_hint?: DecisionOutcome | null;

  suggested_base_score: number;
  suggested_weight: number;
  suggested_hard_decline: boolean;

  support_count: number;
  confidence: number;
  lift?: number | null;

  aligned_decline_reason_codes: string[];

  llm_explanation?: string | null;
}

export interface ProfileRuleConfig {
  rule: RuleCandidate;
  weight_override: number;
  hard_decline: boolean;
  active: boolean;
}

export interface DecisionProfile {
  id?: string;
  name: string;
  description?: string | null;
  approval_threshold: number;
  rules: ProfileRuleConfig[];

  created_at?: string | null;
  created_by?: string | null;

  source_application_ids: string[];
  llm_explanation?: string | null;

  // client-only fields:
  _savedAt?: string;          // when stored in local storage
  _origin?: "mined" | "manual";
}

export interface RuleEvaluation {
  rule_id: string;          // rule_instance_id
  rule_name?: string | null;

  fired: boolean;
  rule_score: number;
  match_details?: string | null;

  decline_reason_codes: string[];
}

export interface ProfileDecisionResult {
  profile_id: string;
  profile_name: string;

  total_score: number;
  decision: ProfileDecision;
  hard_decline_triggered: boolean;

  rule_evaluations: RuleEvaluation[];
  decline_reason_codes: string[];
}

export interface ApplicationDecisionResult {
  application_id: string;

  manual_decision_source?: DecisionSource | null;
  manual_final_decision?: DecisionOutcome | null;
  manual_decline_reasons: DeclineReason[];

  profile_results: ProfileDecisionResult[];

  final_system_decision: ProfileDecision;
  needs_manual_review: boolean;

  aggregated_decline_reason_codes: string[];
}

export interface RuleMinerSummaryMetrics {
  num_loans_analyzed: number;
  num_loans_train?: number | null;
  num_loans_validation?: number | null;
  train_match_rate?: number | null;
  validation_match_rate?: number | null;
  train_auto_decision_rate?: number | null;
  validation_auto_decision_rate?: number | null;
  false_approvals?: number | null;
  false_declines?: number | null;
}

export interface RuleMinerResponse {
  candidate_profile: DecisionProfile;
  summary_metrics: RuleMinerSummaryMetrics;
}

// Saved decision run metadata
export interface SavedDecisionRun {
  id: string;
  name: string;
  createdAt: string;
  applications: Application[];
  profiles: DecisionProfile[];
  results: ApplicationDecisionResult[];
}


export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: number;
}

export interface ChatSession {
  id: string;
  title: string;
  applicationIds: string[]; // which apps this chat is about
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}
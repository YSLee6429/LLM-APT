export type ComponentState = string;

export interface ReadinessResponse {
  status: string;
  service: string;
  version: string;
  checked_at: string;
  components: Record<string, ComponentState>;
}

export interface TestCaseDefinition {
  case_id: string;
  standard_input: string;
  expected_output: string;
  hidden?: boolean;
}

export interface ResourceLimitsDefinition {
  time_limit_ms: number;
  memory_limit_mb: number;
  process_limit?: number;
  output_limit_bytes?: number;
}

export interface ProblemDefinition {
  problem_id: string;
  title: string;
  statement: string;
  language: string;
  tests: TestCaseDefinition[];
  limits: ResourceLimitsDefinition;
  output_policy?: "exact" | "trim_trailing_whitespace" | "token";
}

export interface ProblemValidationResponse {
  valid: boolean;
  problem_id: string;
  test_count: number;
  statement_digest: string;
  test_suite_digest: string;
}

export type MockScenario = "accepted" | "wrong_answer" | "compile_error";
export type Verdict =
  | "accepted"
  | "wrong_answer"
  | "compile_error"
  | "runtime_error"
  | "time_limit_exceeded"
  | "memory_limit_exceeded"
  | "output_limit_exceeded"
  | "infrastructure_error"
  | "inconclusive";

export interface CaseEvaluationResponse {
  case_id: string;
  verdict: Verdict;
  duration_ms: number;
  input_digest: string;
  expected_output_digest: string;
  actual_output_digest: string;
}

export interface MockEvaluationResponse {
  run_id: string;
  problem_id: string;
  verdict: Verdict;
  evidence_level: 0 | 1 | 2 | 3 | 4;
  passed_cases: number;
  total_cases: number;
  cases: CaseEvaluationResponse[];
  ephemeral_artifacts: boolean;
}

export type WorkspaceRole = "admin" | "guest" | "reviewer" | "researcher" | "viewer";

export interface WorkspaceUser {
  user_id: string;
  username: string;
  display_name: string;
  role: WorkspaceRole;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
  user: WorkspaceUser;
}

export interface Project {
  project_id: string;
  name: string;
  description: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  resource_count: number;
  model_profile_count: number;
}

export interface ModelProfile {
  profile_id: string;
  project_id: string;
  name: string;
  provider: string;
  model: string;
  revision: string | null;
  description: string;
  tags: string[];
  created_at: string;
}

export interface ExperimentSummary {
  experiment_id: string;
  created_at: string;
  problem_id: string;
  provider: string;
  model: string;
  status: string;
  repetitions: number;
  plan_digest: string;
}

export interface CandidateSummary {
  candidate_id: string;
  created_at: string;
  parent_problem_id: string;
  operator: string;
  status: string;
  oracle_validation_id: string | null;
}

export interface EvidenceSummary {
  report_id: string;
  candidate_id: string;
  created_at: string;
  provider: string;
  model: string;
  verdict: Verdict;
  evidence_level: number;
  stable_failure: boolean;
  repetitions_completed: number;
  has_counterexample: boolean;
}

export interface DashboardData {
  projects: number;
  model_profiles: number;
  experiments: number;
  candidates: number;
  evidence_reports: number;
  stable_failures: number;
  verdict_counts: Record<string, number>;
  experiment_status_counts: Record<string, number>;
  candidate_status_counts: Record<string, number>;
  recent_experiments: ExperimentSummary[];
  recent_evidence: EvidenceSummary[];
}

export interface ClosedLoopReport {
  report_id: string;
  candidate_id: string;
  oracle_validation_id: string;
  created_at: string;
  target: { provider: string; model: string; revision: string | null };
  repetitions_requested: number;
  repetitions_completed: number;
  verdict: Verdict;
  evidence_level: number;
  stable_failure: boolean;
  observations: Array<{
    repetition: number;
    source_digest: string;
    raw_response_digest: string;
    verdict: Verdict;
    failure_case_id: string | null;
    input_digest: string | null;
    expected_output_digest: string | null;
    actual_output_digest: string | null;
  }>;
  counterexample: null | {
    case_id: string;
    original_input_digest: string;
    minimized_input_digest: string;
    expected_output_digest: string;
    actual_output_digest: string;
    original_size: number;
    minimized_size: number;
    attempts: number;
  };
}

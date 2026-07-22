import type {
  MockEvaluationResponse,
  MockScenario,
  ProblemDefinition,
  ProblemValidationResponse,
  ReadinessResponse,
  CandidateSummary,
  ClosedLoopReport,
  DashboardData,
  EvidenceSummary,
  ExperimentSummary,
  LoginResponse,
  ModelProfile,
  Project,
  WorkspaceUser,
} from "./types";

function readApiBaseUrl(environment: unknown): string {
  if (!environment || typeof environment !== "object" || !("VITE_API_BASE_URL" in environment)) return "";
  const configured: unknown = environment.VITE_API_BASE_URL;
  return typeof configured === "string" ? configured.replace(/\/$/, "") : "";
}

const API_BASE_URL = readApiBaseUrl(import.meta.env);

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function describeErrorBody(body: unknown): string {
  if (typeof body === "string") return body;
  if (body && typeof body === "object" && "detail" in body) {
    const detail: unknown = body.detail;
    return typeof detail === "string" ? detail : JSON.stringify(detail);
  }
  return "请求失败，请检查 API 服务与输入数据。";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  const token = globalThis.sessionStorage.getItem("llmapt_access_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(describeErrorBody(body), response.status);
  return body as T;
}

export function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function fetchCurrentUser(): Promise<WorkspaceUser> {
  return request<WorkspaceUser>("/api/v1/auth/me");
}

export function fetchDashboard(): Promise<DashboardData> {
  return request<DashboardData>("/api/v1/dashboard");
}

export function fetchProjects(): Promise<Project[]> {
  return request<Project[]>("/api/v1/projects");
}

export function createProject(name: string, description: string): Promise<Project> {
  return request<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
}

export function fetchModelProfiles(projectId: string): Promise<ModelProfile[]> {
  return request<ModelProfile[]>(`/api/v1/projects/${projectId}/model-profiles`);
}

export function createModelProfile(
  projectId: string,
  profile: Omit<ModelProfile, "profile_id" | "project_id" | "created_at">,
): Promise<ModelProfile> {
  return request<ModelProfile>(`/api/v1/projects/${projectId}/model-profiles`, {
    method: "POST",
    body: JSON.stringify(profile),
  });
}

export function fetchExperiments(): Promise<ExperimentSummary[]> {
  return request<ExperimentSummary[]>("/api/v1/dashboard/experiments");
}

export function fetchCandidates(): Promise<CandidateSummary[]> {
  return request<CandidateSummary[]>("/api/v1/dashboard/candidates");
}

export function fetchEvidence(projectId?: string): Promise<EvidenceSummary[]> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return request<EvidenceSummary[]>(`/api/v1/reports${query}`);
}

export function fetchReport(reportId: string): Promise<ClosedLoopReport> {
  return request<ClosedLoopReport>(`/api/v1/reports/${reportId}`);
}

export async function downloadReport(
  reportId: string,
  format: "json" | "markdown" | "csv",
): Promise<void> {
  const token = globalThis.sessionStorage.getItem("llmapt_access_token");
  const response = await fetch(
    `${API_BASE_URL}/api/v1/reports/${reportId}/export?format=${format}`,
    { headers: token ? { Authorization: `Bearer ${token}` } : undefined },
  );
  if (!response.ok) throw new ApiError("报告导出失败。", response.status);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `llm-apt-report-${reportId}.${format === "markdown" ? "md" : format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function fetchReadiness(): Promise<ReadinessResponse> {
  return request<ReadinessResponse>("/health/ready");
}

export function validateProblem(problem: ProblemDefinition): Promise<ProblemValidationResponse> {
  return request<ProblemValidationResponse>("/api/v1/problems/validate", {
    method: "POST",
    body: JSON.stringify(problem),
  });
}

export function runMockEvaluation(
  problemId: string,
  scenario: MockScenario,
): Promise<MockEvaluationResponse> {
  return request<MockEvaluationResponse>(`/api/v1/evaluations/mock?problem_id=${encodeURIComponent(problemId)}`, {
    method: "POST",
    body: JSON.stringify({ scenario, random_seed: 7 }),
  });
}

import { afterEach, describe, expect, it, vi } from "vitest";
import type { ApiError } from "./client";
import { fetchReadiness, runMockEvaluation, validateProblem } from "./client";
import { exampleProblem } from "../data/exampleProblem";

afterEach(() => { vi.unstubAllGlobals(); });

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("API client", () => {
  it("reads readiness from the backend", async () => {
    const payload = {
      status: "ready", service: "llm-apt-api", version: "0.2.0",
      checked_at: "2026-07-19T00:00:00Z", components: { database: "ready" },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(payload)));
    await expect(fetchReadiness()).resolves.toEqual(payload);
    expect(fetch).toHaveBeenCalledWith("/health/ready", expect.any(Object));
  });

  it("posts a problem definition for validation", async () => {
    const payload = {
      valid: true, problem_id: exampleProblem.problem_id, test_count: 3,
      statement_digest: "statement", test_suite_digest: "suite",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(payload)));
    await expect(validateProblem(exampleProblem)).resolves.toEqual(payload);
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/problems/validate",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("encodes the problem id when running a mock evaluation", async () => {
    const payload = {
      run_id: "run-1", problem_id: "space id", verdict: "accepted", evidence_level: 2,
      passed_cases: 1, total_cases: 1, cases: [], ephemeral_artifacts: true,
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(payload)));
    await expect(runMockEvaluation("space id", "accepted")).resolves.toEqual(payload);
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/evaluations/mock?problem_id=space%20id",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("surfaces FastAPI detail as an ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "invalid problem" }, 422)));
    await expect(validateProblem(exampleProblem)).rejects.toEqual(
      expect.objectContaining<ApiError>({ name: "ApiError", message: "invalid problem", status: 422 }),
    );
  });
});

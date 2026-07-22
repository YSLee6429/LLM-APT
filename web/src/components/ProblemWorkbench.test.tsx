import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App as AntdApp } from "antd";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { runMockEvaluation, validateProblem } from "../api/client";
import { ProblemWorkbench } from "./ProblemWorkbench";

vi.mock("../api/client", () => ({
  validateProblem: vi.fn(),
  runMockEvaluation: vi.fn(),
}));

function renderWorkbench() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AntdApp><ProblemWorkbench /></AntdApp>
    </QueryClientProvider>,
  );
}

describe("ProblemWorkbench", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("validates the editable problem schema", async () => {
    vi.mocked(validateProblem).mockResolvedValue({
      valid: true, problem_id: "boundary-last-segment", test_count: 3,
      statement_digest: "statement-digest", test_suite_digest: "suite-digest",
    });
    renderWorkbench();
    await userEvent.click(screen.getByRole("button", { name: /验证 Schema/ }));
    expect(validateProblem).toHaveBeenCalledOnce();
    expect(await screen.findByText(/Schema valid/)).toBeInTheDocument();
  });

  it("renders deterministic evaluation evidence", async () => {
    vi.mocked(runMockEvaluation).mockResolvedValue({
      run_id: "run-accepted", problem_id: "boundary-last-segment", verdict: "accepted",
      evidence_level: 2, passed_cases: 1, total_cases: 1, ephemeral_artifacts: true,
      cases: [{
        case_id: "single", verdict: "accepted", duration_ms: 2,
        input_digest: "input-digest", expected_output_digest: "expected-digest",
        actual_output_digest: "actual-digest",
      }],
    });
    renderWorkbench();
    await userEvent.click(screen.getByRole("button", { name: /运行模拟评测/ }));
    expect(runMockEvaluation).toHaveBeenCalledWith("boundary-last-segment", "accepted");
    expect(await screen.findByText("ACCEPTED")).toBeInTheDocument();
    expect(screen.getByText("run-accepted")).toBeInTheDocument();
  });
});

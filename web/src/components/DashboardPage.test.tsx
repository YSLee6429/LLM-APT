import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { fetchDashboard } from "../api/client";
import { DashboardPage } from "./DashboardPage";

vi.mock("../api/client", () => ({ fetchDashboard: vi.fn() }));

describe("DashboardPage", () => {
  it("renders M3 aggregate metrics", async () => {
    vi.mocked(fetchDashboard).mockResolvedValue({
      projects: 2,
      model_profiles: 3,
      experiments: 4,
      candidates: 5,
      evidence_reports: 6,
      stable_failures: 2,
      verdict_counts: { wrong_answer: 2 },
      experiment_status_counts: { planned: 4 },
      candidate_status_counts: { ready: 5 },
      recent_experiments: [],
      recent_evidence: [],
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><DashboardPage /></QueryClientProvider>);

    expect(await screen.findByRole("heading", { name: "评测仪表盘" })).toBeInTheDocument();
    expect(screen.getByText("2 个稳定失效")).toBeInTheDocument();
    expect(screen.getByText("wrong_answer")).toBeInTheDocument();
  });
});

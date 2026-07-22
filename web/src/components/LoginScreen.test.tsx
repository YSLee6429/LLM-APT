import { App as AntdApp } from "antd";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { login } from "../api/client";
import { LoginScreen } from "./LoginScreen";

vi.mock("../api/client", () => ({ login: vi.fn() }));

describe("LoginScreen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("stores the token and returns the authenticated user", async () => {
    const onAuthenticated = vi.fn();
    vi.mocked(login).mockResolvedValue({
      access_token: "signed-token",
      token_type: "bearer",
      expires_in_seconds: 3600,
      user: {
        user_id: "00000000-0000-0000-0000-000000000001",
        username: "admin",
        display_name: "Administrator",
        role: "admin",
      },
    });
    render(<AntdApp><LoginScreen onAuthenticated={onAuthenticated} /></AntdApp>);

    await userEvent.type(screen.getByLabelText("密码"), "test-password");
    await userEvent.click(screen.getByRole("button", { name: "进入工作区" }));

    expect(await screen.findByText("登录评测工作区")).toBeInTheDocument();
    expect(sessionStorage.getItem("llmapt_access_token")).toBe("signed-token");
    expect(onAuthenticated).toHaveBeenCalledWith(expect.objectContaining({ username: "admin" }));
  });

  it("shows an authentication error", async () => {
    vi.mocked(login).mockRejectedValue(new Error("invalid credentials"));
    render(<AntdApp><LoginScreen onAuthenticated={vi.fn()} /></AntdApp>);

    await userEvent.type(screen.getByLabelText("密码"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "进入工作区" }));

    expect(await screen.findByText("invalid credentials")).toBeInTheDocument();
  });
});

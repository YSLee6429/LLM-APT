import { useQuery } from "@tanstack/react-query";
import { App as AntdApp, ConfigProvider, Skeleton, theme } from "antd";
import { useState } from "react";
import { fetchCurrentUser } from "./api/client";
import type { WorkspaceUser } from "./api/types";
import { LoginScreen } from "./components/LoginScreen";
import { Portal } from "./components/Portal";
import "./styles.css";

export default function App() {
  const [darkMode, setDarkMode] = useState(localStorage.getItem("llmapt_theme") === "dark");
  const [sessionUser, setSessionUser] = useState<WorkspaceUser>();
  const hasStoredToken = Boolean(sessionStorage.getItem("llmapt_access_token"));
  const session = useQuery({
    queryKey: ["session"],
    queryFn: fetchCurrentUser,
    enabled: hasStoredToken && !sessionUser,
    retry: false,
  });
  const user = sessionUser ?? session.data;

  function toggleTheme() {
    setDarkMode((current) => {
      localStorage.setItem("llmapt_theme", current ? "light" : "dark");
      return !current;
    });
  }

  function logout() {
    sessionStorage.removeItem("llmapt_access_token");
    setSessionUser(undefined);
    window.location.reload();
  }

  return (
    <ConfigProvider
      theme={{
        algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: "#2563eb",
          colorInfo: "#2563eb",
          borderRadius: 8,
          fontFamily: "Inter, 'Segoe UI', 'Microsoft YaHei', sans-serif",
        },
      }}
    >
      <AntdApp>
        <div className="app-root" data-theme={darkMode ? "dark" : "light"}>
          {hasStoredToken && session.isPending && !user ? <div className="session-loading"><Skeleton active paragraph={{ rows: 6 }} /></div> : null}
          {(!hasStoredToken || !session.isPending) && !user ? <LoginScreen onAuthenticated={setSessionUser} /> : null}
          {user ? <Portal darkMode={darkMode} onLogout={logout} onThemeChange={toggleTheme} user={user} /> : null}
        </div>
      </AntdApp>
    </ConfigProvider>
  );
}

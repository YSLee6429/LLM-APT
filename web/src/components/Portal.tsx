import {
  ApiOutlined,
  AppstoreOutlined,
  BulbOutlined,
  ExperimentOutlined,
  FileProtectOutlined,
  FolderOpenOutlined,
  LogoutOutlined,
  MoonOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import { Button, Dropdown, Tag } from "antd";
import { lazy, Suspense, useState } from "react";
import type { WorkspaceUser } from "../api/types";
import { SystemStatus } from "./SystemStatus";

const DashboardPage = lazy(async () => ({ default: (await import("./DashboardPage")).DashboardPage }));
const EvidencePage = lazy(async () => ({ default: (await import("./EvidencePage")).EvidencePage }));
const ProblemWorkbench = lazy(async () => ({ default: (await import("./ProblemWorkbench")).ProblemWorkbench }));
const ProjectsPage = lazy(async () => ({ default: (await import("./ProjectsPage")).ProjectsPage }));
const ResearchPage = lazy(async () => ({ default: (await import("./ResearchPage")).ResearchPage }));

type PageKey = "dashboard" | "projects" | "research" | "evidence" | "workbench" | "system";

const menu = [
  { key: "dashboard", icon: <AppstoreOutlined />, label: "仪表盘" },
  { key: "projects", icon: <FolderOpenOutlined />, label: "项目与画像" },
  { key: "research", icon: <ExperimentOutlined />, label: "实验与候选" },
  { key: "evidence", icon: <FileProtectOutlined />, label: "证据与报告" },
  { key: "workbench", icon: <ToolOutlined />, label: "题目工作台" },
  { key: "system", icon: <ApiOutlined />, label: "系统状态" },
] as const;

interface Props {
  darkMode: boolean;
  onThemeChange: () => void;
  onLogout: () => void;
  user: WorkspaceUser;
}

export function Portal({ darkMode, onThemeChange, onLogout, user }: Props) {
  const [page, setPage] = useState<PageKey>("dashboard");
  const content = {
    dashboard: <DashboardPage />,
    projects: <ProjectsPage />,
    research: <ResearchPage />,
    evidence: <EvidencePage />,
    workbench: <div className="page-stack"><ProblemWorkbench /></div>,
    system: <div className="page-stack"><header className="page-header"><div><p className="kicker">INFRASTRUCTURE</p><h1>系统状态</h1></div><p>查看 API 与依赖服务的实时就绪状态。</p></header><SystemStatus /></div>,
  }[page];
  return (
    <div className="portal-shell">
      <aside className="sidebar">
        <div className="sidebar-brand"><span>LLM</span><strong>APT</strong><Tag color="blue">M3</Tag></div>
        <nav aria-label="工作区导航">
          {menu.map((item) => (
            <button className={page === item.key ? "active" : ""} key={item.key} onClick={() => { setPage(item.key); }} type="button">
              {item.icon}<span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-note"><strong>研究版 0.4.0</strong><p>本地单工作区部署。商用多租户与配额属于 M4。</p></div>
      </aside>
      <section className="workspace-shell">
        <header className="topbar">
          <div><span className="health-pulse" /> LOCAL RESEARCH WORKSPACE</div>
          <div className="topbar-actions">
            <Button aria-label="切换主题" icon={darkMode ? <BulbOutlined /> : <MoonOutlined />} onClick={onThemeChange} shape="circle" />
            <Dropdown menu={{ items: [
              { key: "role", label: `角色：${user.role}`, disabled: true },
              { key: "logout", label: "退出登录", icon: <LogoutOutlined />, onClick: onLogout },
            ] }}>
              <button className="user-chip" type="button"><span>{user.display_name.slice(0, 1).toUpperCase()}</span><div><strong>{user.display_name}</strong><small>{user.username}</small></div></button>
            </Dropdown>
          </div>
        </header>
        <main className="workspace-content"><Suspense fallback={<div className="panel">正在加载模块…</div>}>{content}</Suspense></main>
      </section>
    </div>
  );
}

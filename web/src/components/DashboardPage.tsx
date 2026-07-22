import {
  ExperimentOutlined,
  FileProtectOutlined,
  FolderOpenOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Empty, Skeleton, Table, Tag } from "antd";
import { fetchDashboard } from "../api/client";

export function DashboardPage() {
  const query = useQuery({ queryKey: ["dashboard"], queryFn: fetchDashboard });
  if (query.isPending) return <Skeleton active paragraph={{ rows: 10 }} />;
  if (query.isError) return <Empty description="无法读取仪表盘，请检查登录状态与 API。" />;
  const data = query.data;
  const cards = [
    [<FolderOpenOutlined />, "项目", data.projects, "研究任务容器"],
    [<RobotOutlined />, "模型画像", data.model_profiles, "目标模型配置"],
    [<ExperimentOutlined />, "实验", data.experiments, "已冻结实验计划"],
    [<FileProtectOutlined />, "证据报告", data.evidence_reports, `${String(data.stable_failures)} 个稳定失效`],
  ] as const;
  const verdictEntries = Object.entries(data.verdict_counts);
  const maxVerdict = Math.max(1, ...verdictEntries.map(([, value]) => value));
  return (
    <div className="page-stack">
      <header className="page-header">
        <div><p className="kicker">OVERVIEW</p><h1>评测仪表盘</h1></div>
        <p>聚合项目、实验、候选与可复现证据，不将基础设施错误计入模型失败。</p>
      </header>
      <section className="summary-grid">
        {cards.map(([icon, label, value, detail]) => (
          <article className="summary-card" key={label}>
            <span className="summary-icon">{icon}</span>
            <div><small>{label}</small><strong>{value}</strong><p>{detail}</p></div>
          </article>
        ))}
      </section>
      <section className="dashboard-grid">
        <article className="panel">
          <div className="panel-heading"><div><h2>裁决分布</h2><p>当前公开证据报告</p></div></div>
          {verdictEntries.length ? (
            <div className="verdict-bars">
              {verdictEntries.map(([name, value]) => (
                <div key={name}>
                  <span>{name}</span>
                  <i style={{ width: `${String(Math.max(5, value / maxVerdict * 100))}%` }} />
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          ) : <Empty description="完成闭环后显示裁决统计" />}
        </article>
        <article className="panel">
          <div className="panel-heading"><div><h2>候选状态</h2><p>准入状态机分布</p></div></div>
          <div className="status-list">
            {Object.entries(data.candidate_status_counts).map(([name, value]) => (
              <div key={name}><span>{name}</span><strong>{value}</strong></div>
            ))}
            {!Object.keys(data.candidate_status_counts).length ? <Empty description="暂无候选" /> : null}
          </div>
        </article>
      </section>
      <article className="panel">
        <div className="panel-heading"><div><h2>最近实验</h2><p>最近冻结的可重复实验计划</p></div></div>
        <Table
          dataSource={data.recent_experiments}
          locale={{ emptyText: "尚未创建实验" }}
          pagination={false}
          rowKey="experiment_id"
          size="small"
          columns={[
            { title: "题目", dataIndex: "problem_id" },
            { title: "目标", render: (_, row) => `${row.provider}/${row.model}` },
            { title: "重复", dataIndex: "repetitions" },
            { title: "状态", dataIndex: "status", render: (value: string) => <Tag>{value}</Tag> },
            { title: "创建时间", dataIndex: "created_at", render: (value: string) => new Date(value).toLocaleString() },
          ]}
        />
      </article>
    </div>
  );
}

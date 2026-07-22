import { useQuery } from "@tanstack/react-query";
import { Empty, Table, Tag } from "antd";
import { fetchCandidates, fetchExperiments } from "../api/client";
import type { ExperimentSummary } from "../api/types";

export function ResearchPage() {
  const experiments = useQuery({ queryKey: ["experiments"], queryFn: fetchExperiments });
  const candidates = useQuery({ queryKey: ["candidates"], queryFn: fetchCandidates });
  return (
    <div className="page-stack">
      <header className="page-header">
        <div><p className="kicker">PIPELINE</p><h1>实验与候选</h1></div>
        <p>实验计划冻结模型身份与生成参数；候选状态展示 Oracle 和人工准入进度。</p>
      </header>
      <article className="panel">
        <div className="panel-heading"><div><h2>实验计划</h2><p>{experiments.data?.length ?? 0} 条记录</p></div></div>
        <Table
          dataSource={experiments.data ?? []}
          locale={{ emptyText: <Empty description="暂无实验计划" /> }}
          rowKey="experiment_id"
          size="small"
          columns={[
            { title: "题目", dataIndex: "problem_id" },
            { title: "目标", render: (_, row: ExperimentSummary) => `${row.provider}/${row.model}` },
            { title: "重复", dataIndex: "repetitions" },
            { title: "状态", dataIndex: "status", render: (value: string) => <Tag>{value}</Tag> },
            { title: "计划摘要", dataIndex: "plan_digest", render: (value: string) => <code>{value.slice(0, 14)}…</code> },
          ]}
        />
      </article>
      <article className="panel">
        <div className="panel-heading"><div><h2>候选准入队列</h2><p>{candidates.data?.length ?? 0} 条记录</p></div></div>
        <Table
          dataSource={candidates.data ?? []}
          locale={{ emptyText: <Empty description="暂无变异候选" /> }}
          rowKey="candidate_id"
          size="small"
          columns={[
            { title: "父题", dataIndex: "parent_problem_id" },
            { title: "算子", dataIndex: "operator" },
            { title: "状态", dataIndex: "status", render: (value: string) => <Tag color={value === "ready" ? "green" : "blue"}>{value}</Tag> },
            { title: "Oracle", dataIndex: "oracle_validation_id", render: (value: string | null) => value ? <code>{value.slice(0, 12)}…</code> : "待校验" },
            { title: "创建时间", dataIndex: "created_at", render: (value: string) => new Date(value).toLocaleString() },
          ]}
        />
      </article>
    </div>
  );
}

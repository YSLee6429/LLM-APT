import { DownloadOutlined, EyeOutlined, FileProtectOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { App, Button, Descriptions, Drawer, Empty, Segmented, Space, Table, Tag } from "antd";
import { useState } from "react";
import { downloadReport, fetchEvidence, fetchReport } from "../api/client";
import type { EvidenceSummary } from "../api/types";

const verdictColors: Record<string, string> = {
  accepted: "green",
  wrong_answer: "red",
  compile_error: "orange",
  infrastructure_error: "purple",
};

export function EvidencePage() {
  const { message } = App.useApp();
  const [selected, setSelected] = useState<string>();
  const [filter, setFilter] = useState("all");
  const evidence = useQuery({ queryKey: ["evidence"], queryFn: () => fetchEvidence() });
  const detail = useQuery({
    queryKey: ["report", selected],
    queryFn: () => fetchReport(selected ?? ""),
    enabled: Boolean(selected),
  });
  const exportMutation = useMutation({
    mutationFn: ({ id, format }: { id: string; format: "json" | "markdown" | "csv" }) => downloadReport(id, format),
    onError: (error: Error) => void message.error(error.message),
  });
  const rows = (evidence.data ?? []).filter((item) => filter === "all" || item.verdict === filter);
  return (
    <div className="page-stack">
      <header className="page-header">
        <div><p className="kicker">AUDIT</p><h1>证据复核与报告</h1></div>
        <Segmented onChange={(value) => { setFilter(value); }} options={[
          { label: "全部", value: "all" }, { label: "WA", value: "wrong_answer" },
          { label: "AC", value: "accepted" }, { label: "CE", value: "compile_error" },
        ]} value={filter} />
      </header>
      <article className="panel">
        <div className="panel-heading"><div><h2>公开证据索引</h2><p>隐藏输入、源码与原始响应不会出现在该投影中</p></div></div>
        <Table
          dataSource={rows}
          locale={{ emptyText: <Empty description="完成闭环后在此复核证据" /> }}
          rowKey="report_id"
          columns={[
            { title: "裁决", dataIndex: "verdict", render: (value: string) => <Tag color={verdictColors[value]}>{value}</Tag> },
            { title: "目标", render: (_, row: EvidenceSummary) => `${row.provider}/${row.model}` },
            { title: "等级", dataIndex: "evidence_level", render: (value: number) => <strong>L{value}</strong> },
            { title: "稳定", dataIndex: "stable_failure", render: (value: boolean) => value ? "是" : "否" },
            { title: "反例", dataIndex: "has_counterexample", render: (value: boolean) => value ? "已缩减" : "—" },
            { title: "时间", dataIndex: "created_at", render: (value: string) => new Date(value).toLocaleString() },
            { title: "操作", render: (_, row: EvidenceSummary) => <Button icon={<EyeOutlined />} onClick={() => { setSelected(row.report_id); }}>复核</Button> },
          ]}
        />
      </article>
      <Drawer onClose={() => { setSelected(undefined); }} open={Boolean(selected)} size="large" title="证据详情">
        {detail.data ? (
          <div className="evidence-detail">
            <div className="evidence-verdict"><FileProtectOutlined /><div><small>FINAL VERDICT</small><strong>{detail.data.verdict}</strong></div></div>
            <Descriptions bordered column={1} size="small" items={[
              { key: "id", label: "Report ID", children: <code>{detail.data.report_id}</code> },
              { key: "candidate", label: "Candidate ID", children: <code>{detail.data.candidate_id}</code> },
              { key: "target", label: "目标", children: `${detail.data.target.provider}/${detail.data.target.model}` },
              { key: "level", label: "证据等级", children: `L${String(detail.data.evidence_level)}` },
              { key: "stable", label: "重复性", children: `${String(detail.data.repetitions_completed)}/${String(detail.data.repetitions_requested)}；${detail.data.stable_failure ? "稳定" : "未稳定"}` },
              { key: "counter", label: "最小反例", children: detail.data.counterexample ? `${String(detail.data.counterexample.original_size)} B → ${String(detail.data.counterexample.minimized_size)} B` : "无" },
            ]} />
            <h3>重复观察</h3>
            {detail.data.observations.map((item) => (
              <div className="observation" key={item.repetition}>
                <span>#{String(item.repetition)}</span><Tag color={verdictColors[item.verdict]}>{item.verdict}</Tag><code>{item.source_digest.slice(0, 14)}…</code>
              </div>
            ))}
            <Space wrap>
              {(["json", "markdown", "csv"] as const).map((format) => (
                <Button icon={<DownloadOutlined />} key={format} onClick={() => { if (selected) exportMutation.mutate({ id: selected, format }); }}>
                  导出 {format.toUpperCase()}
                </Button>
              ))}
            </Space>
          </div>
        ) : <Empty description="正在读取报告" />}
      </Drawer>
    </div>
  );
}

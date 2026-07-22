import { CloudServerOutlined, ReloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Skeleton, Tag, Tooltip } from "antd";
import { fetchReadiness } from "../api/client";

const componentLabels: Record<string, string> = {
  database: "PostgreSQL",
  redis: "Redis",
  broker: "RabbitMQ",
  object_storage: "MinIO",
};

export function SystemStatus() {
  const query = useQuery({
    queryKey: ["readiness"],
    queryFn: fetchReadiness,
    refetchInterval: 15_000,
    retry: 1,
  });

  return (
    <section className="status-panel" aria-label="系统状态">
      <div className="section-heading compact-heading">
        <div>
          <span className="eyebrow">LIVE INFRASTRUCTURE</span>
          <h2><CloudServerOutlined /> 运行状态</h2>
        </div>
        <Tooltip title="立即刷新">
          <Button
            aria-label="刷新系统状态"
            className="icon-button"
            icon={<ReloadOutlined spin={query.isFetching} />}
            onClick={() => void query.refetch()}
            shape="circle"
          />
        </Tooltip>
      </div>

      {query.isPending ? (
        <Skeleton active paragraph={{ rows: 2 }} />
      ) : query.isError ? (
        <div className="offline-state">
          <span className="status-dot offline" />
          <div><strong>API 暂不可用</strong><small>请确认后端容器已启动</small></div>
        </div>
      ) : (
        <>
          <div className="service-summary">
            <span className="status-dot online" />
            <div>
              <strong>{query.data.service}</strong>
              <small>v{query.data.version} · {query.data.status.toUpperCase()}</small>
            </div>
            <Tag color="success">CONNECTED</Tag>
          </div>
          <div className="component-grid">
            {Object.entries(query.data.components).map(([name, status]) => (
              <div className="component-state" key={name}>
                <span>{componentLabels[name] ?? name}</span>
                <Tag color={status === "ready" ? "cyan" : "error"}>{status}</Tag>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

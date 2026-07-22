import {
  ApiOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";

const nodes = [
  { icon: <ExperimentOutlined />, title: "Problem Mutation", subtitle: "边界与语义变异", state: "M2" },
  { icon: <ApiOutlined />, title: "Model Solver", subtitle: "多模型并行求解", state: "M3" },
  { icon: <SafetyCertificateOutlined />, title: "Judge Sandbox", subtitle: "确定性隔离评测", state: "M1" },
  { icon: <NodeIndexOutlined />, title: "Failure Analysis", subtitle: "证据与失败归因", state: "M4" },
];

export function ArchitectureFlow() {
  return (
    <section className="architecture-section" id="architecture">
      <div className="section-heading">
        <div>
          <span className="eyebrow">GENERATION → EVALUATION → EVOLUTION</span>
          <h2>对抗评测闭环</h2>
        </div>
        <p>每次失败都沉淀为可复核证据，并驱动下一轮候选题目生成。</p>
      </div>
      <div className="flow-grid">
        {nodes.map((node, index) => (
          <div className={`flow-node ${node.state === "M1" ? "active" : ""}`} key={node.title}>
            <span className="flow-index">0{index + 1}</span>
            <span className="flow-icon">{node.icon}</span>
            <strong>{node.title}</strong>
            <small>{node.subtitle}</small>
            <span className="milestone-pill">{node.state}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

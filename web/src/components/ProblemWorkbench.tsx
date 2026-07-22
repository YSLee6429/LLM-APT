import {
  CheckCircleFilled,
  CodeOutlined,
  ExperimentOutlined,
  PlayCircleFilled,
} from "@ant-design/icons";
import { useMutation } from "@tanstack/react-query";
import { App, Button, Progress, Radio, Tag } from "antd";
import { useMemo, useState } from "react";
import { runMockEvaluation, validateProblem } from "../api/client";
import type { MockScenario, ProblemDefinition, Verdict } from "../api/types";
import { exampleProblemJson } from "../data/exampleProblem";

const verdictLabels: Record<Verdict, string> = {
  accepted: "ACCEPTED",
  wrong_answer: "WRONG ANSWER",
  compile_error: "COMPILE ERROR",
  runtime_error: "RUNTIME ERROR",
  time_limit_exceeded: "TIME LIMIT",
  memory_limit_exceeded: "MEMORY LIMIT",
  output_limit_exceeded: "OUTPUT LIMIT",
  infrastructure_error: "INFRA ERROR",
  inconclusive: "INCONCLUSIVE",
};

function parseProblem(source: string): ProblemDefinition {
  const value: unknown = JSON.parse(source);
  if (!value || typeof value !== "object" || !("problem_id" in value)) {
    throw new Error("JSON 中缺少 problem_id。 ");
  }
  return value as ProblemDefinition;
}

function digest(value: string) {
  return value.length > 13 ? `${value.slice(0, 13)}…` : value;
}

export function ProblemWorkbench() {
  const { message } = App.useApp();
  const [source, setSource] = useState(exampleProblemJson);
  const [scenario, setScenario] = useState<MockScenario>("accepted");
  const [problemId, setProblemId] = useState("boundary-last-segment");

  const validation = useMutation({
    mutationFn: async () => validateProblem(parseProblem(source)),
    onSuccess: (data) => {
      setProblemId(data.problem_id);
      void message.success(`Schema valid：已识别 ${String(data.test_count)} 个测试用例`);
    },
    onError: (error: Error) => void message.error(error.message),
  });
  const evaluation = useMutation({
    mutationFn: async () => {
      const parsed = parseProblem(source);
      setProblemId(parsed.problem_id);
      return runMockEvaluation(parsed.problem_id, scenario);
    },
    onError: (error: Error) => void message.error(error.message),
  });

  const result = evaluation.data;
  const passRate = useMemo(
    () => result && result.total_cases > 0 ? Math.round(result.passed_cases / result.total_cases * 100) : 0,
    [result],
  );

  return (
    <section className="workbench-section" id="workbench">
      <div className="section-heading">
        <div>
          <span className="eyebrow">M3 PROBLEM LAB</span>
          <h2>题目验证工作台</h2>
        </div>
        <p>验证 Problem Schema，并调用确定性接口预演 AC、WA 与 CE 证据；正式闭环结果进入证据中心。</p>
      </div>

      <div className="workbench-grid">
        <div className="editor-panel glass-panel">
          <div className="panel-toolbar">
            <div><CodeOutlined /> <strong>problem.json</strong><span className="unsaved-dot" /></div>
            <Tag variant="filled">JSON · UTF-8</Tag>
          </div>
          <label className="sr-only" htmlFor="problem-source">题目定义 JSON</label>
          <textarea
            id="problem-source"
            onChange={(event) => { setSource(event.target.value); }}
            spellCheck={false}
            value={source}
          />
          <div className="editor-actions">
            <Button
              icon={<CheckCircleFilled />}
              loading={validation.isPending}
              onClick={() => { validation.mutate(); }}
            >验证 Schema</Button>
            <Button
              icon={<PlayCircleFilled />}
              loading={evaluation.isPending}
              onClick={() => { evaluation.mutate(); }}
              type="primary"
            >运行模拟评测</Button>
          </div>
        </div>

        <div className="result-panel glass-panel">
          <div className="panel-toolbar scenario-toolbar">
            <div><ExperimentOutlined /> <strong>Evaluation evidence</strong></div>
            <Radio.Group
              buttonStyle="solid"
              onChange={(event) => { setScenario(event.target.value as MockScenario); }}
              optionType="button"
              size="small"
              value={scenario}
            >
              <Radio.Button value="accepted">AC</Radio.Button>
              <Radio.Button value="wrong_answer">WA</Radio.Button>
              <Radio.Button value="compile_error">CE</Radio.Button>
            </Radio.Group>
          </div>

          {!result ? (
            <div className="result-empty">
              <span className="empty-orbit"><ExperimentOutlined /></span>
              <strong>等待评测任务</strong>
              <p>选择 AC、WA 或 CE 场景后运行，结果将展示在这里。</p>
              <small>Current problem · {problemId}</small>
            </div>
          ) : (
            <div className="result-content">
              <div className={`verdict-banner verdict-${result.verdict}`}>
                <div>
                  <span>FINAL VERDICT</span>
                  <strong>{verdictLabels[result.verdict]}</strong>
                  <small>Evidence level L{result.evidence_level} · deterministic mock</small>
                </div>
                <Progress
                  percent={passRate}
                  size={80}
                  strokeColor={result.verdict === "accepted" ? "#39e6b5" : "#ff6b8a"}
                  type="circle"
                />
              </div>
              <div className="run-meta">
                <span>RUN ID</span><code>{result.run_id}</code>
                <span>CASES</span><strong>{result.passed_cases}/{result.total_cases}</strong>
              </div>
              <div className="case-list">
                {result.cases.map((testCase) => (
                  <div className="case-row" key={testCase.case_id}>
                    <span className={`case-indicator ${testCase.verdict}`} />
                    <div><strong>{testCase.case_id}</strong><small>input {digest(testCase.input_digest)}</small></div>
                    <code>{testCase.duration_ms} ms</code>
                    <Tag color={testCase.verdict === "accepted" ? "success" : "error"}>
                      {testCase.verdict === "accepted" ? "PASS" : "FAIL"}
                    </Tag>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

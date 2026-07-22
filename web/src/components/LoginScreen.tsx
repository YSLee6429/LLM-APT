import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input } from "antd";
import { useState } from "react";
import { login } from "../api/client";
import type { WorkspaceUser } from "../api/types";

interface Props {
  onAuthenticated: (user: WorkspaceUser) => void;
}

export function LoginScreen({ onAuthenticated }: Props) {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(values: { username: string; password: string }) {
    setLoading(true);
    setError("");
    try {
      const session = await login(values.username, values.password);
      sessionStorage.setItem("llmapt_access_token", session.access_token);
      onAuthenticated(session.user);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="brand-lockup"><span>LLM</span><strong>APT</strong></div>
        <p className="kicker">RESEARCH EVALUATION WORKSPACE</p>
        <h1>把模型失效转化为<br />可复核的工程证据</h1>
        <p className="login-description">
          本地部署的编程能力边界评测平台，覆盖题目变异、可信 Oracle、隔离执行、
          证据复核和报告导出。
        </p>
        <div className="login-trust">
          <span><SafetyCertificateOutlined /> 本地凭据</span>
          <span><SafetyCertificateOutlined /> 隐藏数据分层</span>
          <span><SafetyCertificateOutlined /> 可重复验收</span>
        </div>
      </section>
      <section className="login-card" aria-label="登录工作区">
        <div>
          <p className="kicker">M3 · COMPLETE</p>
          <h2>登录评测工作区</h2>
          <p>使用部署环境中配置的本地管理员账号。</p>
        </div>
        {error ? <Alert title={error} showIcon type="error" /> : null}
        <Form
          initialValues={{ username: "admin" }}
          layout="vertical"
          onFinish={(values: { username: string; password: string }) => void submit(values)}
          size="large"
        >
          <Form.Item label="用户名" name="username" rules={[{ required: true }]}>
            <Input autoComplete="username" prefix={<UserOutlined />} />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" prefix={<LockOutlined />} />
          </Form.Item>
          <Button block htmlType="submit" loading={loading} type="primary">进入工作区</Button>
        </Form>
        <small>管理员密码保存在本机 .env 中；请勿提交或分享该文件。</small>
      </section>
    </main>
  );
}

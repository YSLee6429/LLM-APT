import { PlusOutlined, RobotOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Empty, Form, Input, List, Modal, Select, Tag } from "antd";
import { useState } from "react";
import {
  createModelProfile,
  createProject,
  fetchModelProfiles,
  fetchProjects,
} from "../api/client";
import type { ModelProfile, Project } from "../api/types";

export function ProjectsPage() {
  const { message } = App.useApp();
  const cache = useQueryClient();
  const projects = useQuery({ queryKey: ["projects"], queryFn: fetchProjects });
  const [selected, setSelected] = useState<string>();
  const [projectModal, setProjectModal] = useState(false);
  const [profileModal, setProfileModal] = useState(false);
  const projectId = selected ?? projects.data?.[0]?.project_id;
  const profiles = useQuery({
    queryKey: ["profiles", projectId],
    queryFn: () => fetchModelProfiles(projectId ?? ""),
    enabled: Boolean(projectId),
  });
  const addProject = useMutation({
    mutationFn: (value: { name: string; description: string }) => createProject(value.name, value.description),
    onSuccess: (project) => {
      setSelected(project.project_id);
      setProjectModal(false);
      void cache.invalidateQueries({ queryKey: ["projects"] });
      void cache.invalidateQueries({ queryKey: ["dashboard"] });
      void message.success("项目已创建");
    },
    onError: (error: Error) => void message.error(error.message),
  });
  const addProfile = useMutation({
    mutationFn: (value: Omit<ModelProfile, "profile_id" | "project_id" | "created_at">) =>
      createModelProfile(projectId ?? "", value),
    onSuccess: () => {
      setProfileModal(false);
      void cache.invalidateQueries({ queryKey: ["profiles", projectId] });
      void cache.invalidateQueries({ queryKey: ["projects"] });
      void message.success("模型画像已保存");
    },
    onError: (error: Error) => void message.error(error.message),
  });
  const active = projects.data?.find((item) => item.project_id === projectId);

  return (
    <div className="page-stack">
      <header className="page-header">
        <div><p className="kicker">ORGANIZATION</p><h1>项目与模型画像</h1></div>
        <Button icon={<PlusOutlined />} onClick={() => { setProjectModal(true); }} type="primary">新建项目</Button>
      </header>
      <section className="projects-layout">
        <aside className="panel project-list">
          <div className="panel-heading"><div><h2>研究项目</h2><p>{projects.data?.length ?? 0} 个项目</p></div></div>
          <List
            dataSource={projects.data ?? []}
            locale={{ emptyText: "新建项目以组织实验与证据" }}
            renderItem={(project: Project) => (
              <button
                className={project.project_id === projectId ? "project-row selected" : "project-row"}
                onClick={() => { setSelected(project.project_id); }}
                type="button"
              >
                <strong>{project.name}</strong>
                <span>{project.model_profile_count} 个画像 · {project.resource_count} 个资源</span>
              </button>
            )}
          />
        </aside>
        <article className="panel project-detail">
          {active ? (
            <>
              <div className="panel-heading">
                <div><h2>{active.name}</h2><p>{active.description || "暂无项目说明"}</p></div>
                <Button icon={<RobotOutlined />} onClick={() => { setProfileModal(true); }}>添加模型画像</Button>
              </div>
              <div className="profile-grid">
                {(profiles.data ?? []).map((profile) => (
                  <article className="profile-card" key={profile.profile_id}>
                    <span className="summary-icon"><RobotOutlined /></span>
                    <h3>{profile.name}</h3>
                    <code>{profile.provider}/{profile.model}{profile.revision ? `@${profile.revision}` : ""}</code>
                    <p>{profile.description || "未填写说明"}</p>
                    <div>{profile.tags.map((tag) => <Tag key={tag}>{tag}</Tag>)}</div>
                  </article>
                ))}
                {!profiles.isPending && !profiles.data?.length ? <Empty description="尚未添加模型画像" /> : null}
              </div>
            </>
          ) : <Empty description="请选择或新建一个项目" />}
        </article>
      </section>
      <Modal footer={null} onCancel={() => { setProjectModal(false); }} open={projectModal} title="新建研究项目">
        <Form layout="vertical" onFinish={(value: { name: string; description: string }) => { addProject.mutate(value); }}>
          <Form.Item label="项目名称" name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="项目说明" name="description"><Input.TextArea rows={4} /></Form.Item>
          <Button block htmlType="submit" loading={addProject.isPending} type="primary">创建项目</Button>
        </Form>
      </Modal>
      <Modal footer={null} onCancel={() => { setProfileModal(false); }} open={profileModal} title="添加模型画像">
        <Form
          initialValues={{ provider: "local", tags: ["baseline"] }}
          layout="vertical"
          onFinish={(value: { name: string; provider: string; model: string; revision?: string; description?: string; tags?: string[] }) => { addProfile.mutate({
            name: value.name,
            provider: value.provider,
            model: value.model,
            revision: value.revision ?? null,
            description: value.description ?? "",
            tags: value.tags ?? [],
          }); }}
        >
          <Form.Item label="画像名称" name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <div className="form-two-columns">
            <Form.Item label="Provider" name="provider" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item label="模型" name="model" rules={[{ required: true }]}><Input /></Form.Item>
          </div>
          <Form.Item label="版本" name="revision"><Input /></Form.Item>
          <Form.Item label="说明" name="description"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item label="标签" name="tags"><Select mode="tags" /></Form.Item>
          <Button block htmlType="submit" loading={addProfile.isPending} type="primary">保存模型画像</Button>
        </Form>
      </Modal>
    </div>
  );
}

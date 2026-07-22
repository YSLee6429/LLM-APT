# LLM-APT 0.4.0 最终提交说明

本目录是 M0—M3 的最终本地研究预览版本，可作为课程项目、研究 Demo 或 GitHub 开源工程提交。M4 商用能力未开发，并已在论文和路线图中标为后续工作。

## 快速启动

在项目目录中生成随机本地配置并启动：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
docker compose up -d --build
docker compose ps
```

访问：

- 网站：<http://localhost:3000>
- API 文档：<http://localhost:8000/docs>
- 管理员账号与密码：查看本机 `.env` 中的 `LLMAPT_BOOTSTRAP_ADMIN_*`
- 游客后端入口：`POST /api/v1/auth/guest`

`.env` 由配置脚本随机生成，不应提交或放入公开源码包。已有旧数据卷升级时请按本地部署说明书同步数据库服务密码。

## 本地质量校验

```bash
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov-fail-under=80

cd web
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test -- --run
pnpm build
```

## 提交内容

- Python/FastAPI 控制面、Celery Worker 和 PostgreSQL 持久化
- 独立 C++20 Runner
- React/TypeScript 评测工作台
- Docker Compose 八服务部署
- M0—M3 设计、路线图、验收和开发记录
- 论文 DOCX/PDF（位于提交合集的 `论文` 目录）

## 结论边界

0.4.0 已通过 120 项后端测试、9 项前端测试、82.86% 覆盖率门禁、八服务健康检查、闭环样本与浏览器工作区流程。该结果证明工程机制可运行、可复现和可审计，不证明任何真实商业模型的总体能力优劣。

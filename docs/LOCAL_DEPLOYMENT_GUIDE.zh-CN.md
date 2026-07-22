# LLM-APT 本地部署与使用说明书

本文面向第一次接触 Docker、API 或在线评测系统的使用者。按照“准备环境—生成配置—启动—登录—校验”的顺序操作，即可在本机运行 LLM-APT 0.4.0 Research Preview。该版本适合本地研究、教学演示和二次开发，不应直接暴露到公网或作为多租户商业服务。

## 1. 这个工具能做什么

LLM-APT 用来研究大型语言模型在程序设计任务中的稳定失败。它可以管理题目与模型画像、生成边界变体、用可信 Oracle 检查题目、调用模型生成代码、在隔离 Runner 中编译执行、重复验证失败，并把反例与运行信息整理成可导出的证据报告。

系统默认提供本地确定性 Provider，因此没有模型 API Key 也能启动、浏览和完成工程验收。真实模型调用需要使用者自行提供兼容的 HTTPS API，并在本地 `.env` 中开启。

## 2. 版本边界

- 已完成：M0 基础设施、M1 题目与评测基础、M2 闭环评测、M3 研究工作区与证据导出。
- 已完成的安全基线：随机本地密钥、管理员与游客会话、角色鉴权、登录限流、项目所有权隔离、Runner 非 root 与资源限制。
- 尚未实现：M4 多租户隔离、配额和计费、集中密钥托管、商业审计后台、逐任务虚拟机和服务等级承诺。
- 当前执行语言：C++20。新增语言必须增加独立受控 Runner 和判题适配器。

## 3. 准备环境

### 3.1 推荐硬件

- 4 核或以上 CPU；
- 8 GB 或以上内存，推荐 16 GB；
- 8 GB 以上可用磁盘空间；
- 能够下载 Docker 镜像和项目依赖的网络。

### 3.2 Windows 10/11

安装下列软件：

1. Docker Desktop，并在设置中使用 WSL 2 backend；
2. Git for Windows；
3. Windows Terminal 或 PowerShell 5.1 以上版本。

启动 Docker Desktop，等待界面显示 Engine running。仅使用 Docker 部署时，无须单独安装 Python、Node.js、PostgreSQL、Redis、RabbitMQ、MinIO 或 C++ 编译器。

### 3.3 Linux 或 macOS

安装 Docker Engine（或 Docker Desktop）、Docker Compose v2、Git、curl 和 Bash。确认以下命令均能运行：

```bash
docker version
docker compose version
git --version
```

## 4. 获取项目

如果从 GitHub 获取：

```bash
git clone https://github.com/YSLee6429/LLM-APT.git
cd llm-apt
```

如果使用最终提交压缩包，先完整解压，再进入含有 `compose.yaml`、`README.md` 和 `scripts` 目录的“工程源码”文件夹。不要直接在压缩包预览窗口中运行脚本。

## 5. 生成本地配置

配置脚本会在项目根目录生成 `.env`，其中包含数据库、消息队列、Runner、会话签名和管理员账号的随机凭据。

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
```

Linux、macOS 或 WSL：

```bash
chmod +x ./scripts/setup-local.sh ./scripts/smoke-test.sh
./scripts/setup-local.sh
```

`.env` 已被 Git 忽略。不要把它上传到 GitHub、网盘公开链接、论文、截图或聊天记录中。

查看首次管理员账号：

```powershell
Select-String -Path .env -Pattern 'LLMAPT_BOOTSTRAP_ADMIN_(USERNAME|PASSWORD)'
```

```bash
grep 'LLMAPT_BOOTSTRAP_ADMIN_\(USERNAME\|PASSWORD\)' .env
```

请把密码存入可信密码管理器。系统初始化后，`.env` 中的 bootstrap 密码不会覆盖数据库内已有管理员密码。

## 6. 构建并启动

在项目根目录执行：

```bash
docker compose up -d --build
```

第一次运行需要下载镜像并编译前后端，耗时取决于网络和机器性能。随后查看状态：

```bash
docker compose ps
```

正常情况下应看到 8 个服务：`api`、`worker`、`web`、`runner`、`postgres`、`rabbitmq`、`redis` 和 `minio`。状态最终应为 `running` 或 `healthy`。刚启动时短暂显示 `starting` 属于正常现象，可等待约 30 秒后再次检查。

## 7. 打开系统

- 评测网站：<http://localhost:3000>
- API 交互文档：<http://localhost:8000/docs>
- API 就绪检查：<http://localhost:8000/health/ready>

当前前端使用管理员登录入口。输入 `.env` 中的管理员用户名和密码即可进入研究工作区。后端已经支持 `POST /api/v1/auth/guest` 创建短时游客会话；游客可使用自己的临时项目和安全演示接口，但不能调用外部模型、Oracle、闭环评测或全局报告。游客按钮将在后续前端交互调整中接入。

## 8. 一键校验部署

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1
```

Linux、macOS 或 WSL：

```bash
./scripts/smoke-test.sh
```

脚本依次检查 API 存活、依赖就绪、游客令牌、游客禁止调用外部模型以及 Web 首页。最后显示“冒烟校验通过”才表示基础部署可用。该脚本不会读取管理员密码，不会调用真实模型，也不会删除数据。

## 9. 新手使用流程

1. 登录后先在“项目”中建立研究项目，用名称和说明标记本次实验目的。
2. 为项目登记模型画像，记录 Provider、模型名、版本和标签。版本信息应尽量精确，便于复现。
3. 在题目工作台录入题面、输入输出约束、测试和资源限制，并先执行结构校验。
4. 选择变异算子生成候选。候选必须经过 Oracle 校验和必要的人工审核，才能进入正式闭环。
5. 先使用本地确定性 Provider 熟悉流程，再接入真实模型。小规模连通测试成功后再增加重复次数。
6. 在证据中心查看判定、稳定失败、最小反例和摘要，按需导出 JSON、Markdown 或 CSV。
7. 论文或报告中应同时记录模型版本、提示、题目版本、随机种子、预算、运行日期和失败证据等级。

LLM-APT 发现的是“在给定题目、测试和执行环境下可复现的失败”，不是对模型总体能力的直接排名。没有经过 Oracle 验证、重复执行和最小反例确认的结果，不应写成模型能力结论。

## 10. 修改管理员密码

先通过 `/api/v1/auth/login` 登录获得 Bearer 令牌，再调用：

```bash
curl -X POST http://localhost:8000/api/v1/auth/change-password \
  -H "Authorization: Bearer <登录令牌>" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"<旧密码>","new_password":"<至少12位的新密码>"}'
```

浏览器令牌保存在 `sessionStorage`，关闭标签页后消失。不要在公共电脑或不可信浏览器中登录管理员账号。

## 11. 配置真实模型 API

外部模型调用默认关闭。确认离线流程正常后，在 `.env` 中设置：

```dotenv
LLMAPT_EXTERNAL_MODEL_CALLS_ENABLED=true
LLMAPT_MODEL_PROVIDER_KEY=external
LLMAPT_MODEL_PROVIDER_NAME=openai-compatible
LLMAPT_MODEL_NAME=<服务商公布的模型名称>
LLMAPT_MODEL_REVISION=<可选的精确版本>
LLMAPT_MODEL_API_ENDPOINT=https://<服务商地址>/v1/chat/completions
LLMAPT_MODEL_API_KEY=<你的API-Key>
```

然后只重建需要读取配置的服务：

```bash
docker compose up -d --build api worker
```

不同服务商虽然声称兼容 OpenAI 接口，字段、限流和响应格式仍可能不同。首次只提交一个公开的小题目，并确认响应、费用和日志中没有泄露密钥。API Key 只能保存在本机 `.env` 或秘密管理系统。

## 12. 查看日志与排障

查看所有服务最近日志：

```bash
docker compose logs --tail=100
```

持续查看 API：

```bash
docker compose logs --follow api
```

常见问题：

### 12.1 网页打不开

先执行 `docker compose ps`。若 `web` 或 `api` 未启动，查看对应日志；确认 3000 和 8000 端口未被其他程序占用。Windows 还应确认 Docker Desktop 仍在运行。

### 12.2 页面打开但没有数据

新数据库本来就是空的，需要先登录并创建项目。若浏览器保留了失效会话，关闭标签页后重新登录，或清除该站点的 `sessionStorage`。

### 12.3 服务一直不健康

执行：

```bash
docker compose config --quiet
docker compose logs --tail=200 <服务名>
```

若是首次部署，优先检查 `.env` 是否由脚本完整生成。若旧数据卷来自另一份 `.env`，数据库或 RabbitMQ 的持久化密码可能与新配置不一致；先备份数据，再恢复原 `.env`。不要为了排障直接删除数据卷。

### 12.4 登录失败

确认输入的是 bootstrap 用户名和数据库当前密码。连续失败会触发短时限流并返回 HTTP 429，等待约 60 秒后重试。数据库已初始化后，修改 `.env` 不会重置已有密码。

### 12.5 Runner 编译或执行失败

确认 `runner` 为 healthy。代码仅支持 C++20；资源限制过小、语法错误、超时、超内存和输出超限会得到不同判定。Runner 没有宿主机端口，外部不能直接访问是预期设计。

## 13. 停止、备份和更新

停止但保留数据：

```bash
docker compose down
```

重新启动：

```bash
docker compose up -d
```

升级前至少备份 `.env`、PostgreSQL 数据以及需要保留的证据导出文件。更新源码后执行：

```bash
docker compose up -d --build
docker compose ps
```

`docker compose down -v` 会删除数据库、消息队列、缓存和对象存储卷，通常不可恢复。只有明确希望清空全部本地数据时才能执行。

## 14. 开发者质量校验

后端：

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=llmapt --cov-fail-under=80
```

前端：

```bash
cd web
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test -- --run
pnpm build
```

0.4.0 当前验收基线为：120 项后端测试全部通过，覆盖率 82.86%；4 个前端测试文件中的 9 项测试全部通过；8 个 Docker 服务健康；Runner 的正常执行与内存超限实测均符合预期。

## 15. 安全提醒

- 不要提交 `.env`、API Key、隐藏测试、模型原始响应或私人题目。
- 不要把 0.4.0 直接暴露到公网，也不要允许不受信任的多租户任意提交代码。
- 对公开报告使用系统提供的脱敏导出，不公开源码、原始模型响应和内部资源标识。
- 发现安全问题时按 `SECURITY.md` 私下报告，不要在公开 Issue 中粘贴利用方法或凭据。

完成上述部署与冒烟校验后，系统已经具备本地研究和演示条件。接入真实模型前，建议先保存一份干净快照，并用公开、低成本的小样本确认接口兼容性。

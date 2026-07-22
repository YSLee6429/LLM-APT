# LLM-APT 0.4.0 核心加固与复验记录

- 验收日期：2026-07-22（Asia/Shanghai）
- 验收范围：身份认证、游客权限、配置安全、Runner 资源判定、后端与前端质量门禁、Docker 部署
- 验收结论：通过，可作为本地开源研究预览版提交；不构成 M4 商用或公网多租户安全认证

## 1. 本轮修正

1. 新增短时游客会话，游客项目按所有者隔离。
2. 游客仅可使用项目、题目校验、Mock 评测和变异预览等安全接口；外部模型、实验、Oracle、闭环和全局证据报告均拒绝访问。
3. 人工审核统一使用 Bearer 令牌及管理员/审核员角色，不再支持旧式共享审核令牌。
4. 新增管理员修改密码接口及登录失败限流；连续失败达到阈值后短时返回 HTTP 429。
5. 浏览器会话令牌由 `localStorage` 改为 `sessionStorage`，登录页不再预填默认密码。
6. 生产配置拒绝默认或过短的 Runner 令牌、会话签名密钥和管理员初始密码。
7. 本地初始化脚本随机生成 `.env` 凭据，`.env` 保持 Git 忽略。
8. Runner 使用 `/usr/bin/time` 记录峰值内存，并结合分配失败特征判定 MLE；执行结束保证清理残留进程。
9. 新增 Windows 与 Bash 冒烟脚本，校验 API、游客权限和 Web 入口。

## 2. 自动化质量门禁

| 检查项 | 结果 |
|---|---|
| Ruff 代码检查 | 通过，0 error |
| Ruff 格式检查 | 117 个文件通过 |
| MyPy | 76 个源文件通过，0 issue |
| Pytest | 120/120 通过 |
| Python 覆盖率 | 82.86%，阈值 80% |
| ESLint | 通过，0 warning |
| TypeScript | 严格检查通过 |
| Vitest | 4 个文件、9/9 测试通过 |
| Vite 生产构建 | 通过 |

Pytest 输出包含一条第三方 Starlette TestClient 弃用警告，不影响当前运行；待上游生态完成迁移后再更新测试客户端。

## 3. Docker 与接口冒烟验证

`api`、`worker`、`web`、`runner`、`postgres`、`rabbitmq`、`redis` 和 `minio` 八个服务均为 healthy。

Windows PowerShell 与 Bash 两套 `smoke-test` 均通过以下检查：

- `/health/live` 返回 `status=ok`；
- `/health/ready` 返回 `status=ready`；
- 可创建 role 为 `guest` 的短时会话；
- 游客调用 Provider 生成接口返回 HTTP 403；
- Web 入口返回 HTTP 200。

## 4. Runner 真实执行

| 场景 | 输入/限制 | 实际结果 | 结论 |
|---|---|---|---|
| 正常 C++20 | 输入 21，计算两倍 | 编译成功；exit=0；stdout=42 | 通过 |
| 内存超限 | 32 MiB 限制，尝试分配并写入 256 MiB | exit=134；memory_exceeded=true；infrastructure_error=false | 通过 |

Runner 没有宿主机公开端口，测试从容器内部携带短期内部令牌完成。验收记录不保存令牌或 `.env` 内容。

## 5. 已知边界

- 当前 Runner 是共享研究容器，不是逐任务微型虚拟机。
- 游客记录会保存在本地数据库，自动过期清理尚未实现。
- 当前仅支持 C++20。
- 未使用真实外部模型样本，不对模型优劣、失败命中率或商业安全性作统计结论。
- M4 多租户、配额、计费、密钥托管、可观测性与 SLA 属于后续工作。

## 6. 复验命令

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=llmapt --cov-fail-under=80

cd web
pnpm lint
pnpm typecheck
pnpm test -- --run
pnpm build

docker compose ps
```

Windows 冒烟测试：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1
```

Bash 冒烟测试：

```bash
./scripts/smoke-test.sh
```

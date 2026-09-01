# AI Agent Task Platform

这是一个学习型但接近生产分层的 Python 后端项目。它围绕“创建并运行 AI Agent 任务”这一条业务主线，串联 FastAPI、Pydantic、SQLAlchemy 2.x、PostgreSQL、Alembic、JWT、事务、后台任务与 SSE。

当前实施状态：**第二阶段已完成**。项目已具备 PostgreSQL ORM、Session 生命周期、Repository 数据访问层以及可执行、可回滚的 Alembic 初始迁移；认证和 Agent 业务将在第三阶段加入。

## 技术栈

- Python 3.11+
- FastAPI / Uvicorn
- Pydantic v2 / pydantic-settings
- SQLAlchemy 2.x / Alembic
- PostgreSQL 16 / psycopg2
- PyJWT / bcrypt
- httpx / pytest

## 项目结构

```text
ai-agent-task-platform/
├── app/
│   ├── main.py                 # 应用工厂、路由和中间件注册
│   ├── api/v1/                 # v1 业务接口
│   ├── core/                   # 配置、异常、日志和安全能力
│   ├── db/                     # Session、Base 和 ORM 模型
│   ├── schemas/                # Pydantic 请求与响应模型
│   ├── repositories/           # SQLAlchemy 数据访问
│   ├── services/               # 业务规则与事务边界
│   ├── middlewares/            # 请求上下文中间件
│   └── utils/                  # 通用工具
├── alembic/                    # Alembic 迁移脚本与版本历史
├── tests/                      # pytest 测试
├── AGENTS.md                   # 项目协作约束
├── LEARNING_PATH.md            # 中文学习路线
├── pyproject.toml
├── .env.example
└── docker-compose.yml
```

## 环境准备与启动

### 1. 启动 PostgreSQL

```bash
docker compose up -d
```

本机 Docker Desktop 采用了当前用户目录安装方式。如果新 PowerShell 窗口中提示找不到 `docker`，可以直接使用完整路径：

```powershell
& "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe" compose up -d
```

这只会启动本项目定义的 PostgreSQL，不会修改已经运行的 Redis 容器。

检查容器：

```bash
docker compose ps
```

### 2. 创建并激活虚拟环境

PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -e ".[dev]"
```

### 4. 配置环境变量

PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS / Linux：

```bash
cp .env.example .env
```

部署到共享环境前必须替换 `JWT_SECRET_KEY`，不能使用示例值。
项目根目录的 `.env` 已被 `.gitignore` 排除，不应提交到版本库；`.env.example` 只保存可公开的配置模板。

### 5. 数据库迁移

初始迁移已经提交在 `alembic/versions/`。新环境请执行：

```bash
alembic upgrade head
```

模型发生结构变化后，再生成新的迁移并执行：

```bash
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

学习或本地验证时可以回滚最近一版：

```bash
alembic downgrade -1
```

生产环境不能使用 `Base.metadata.create_all()` 管理表结构。`create_all()` 不会形成可审核、可回滚的版本历史，生产改表必须通过 Alembic migration。

## 第二阶段：数据库模型与迁移

初始 migration 创建以下四张表：

- `users`：用户名唯一索引，密码字段仅用于保存哈希值。
- `agent_tasks`：通过 `user_id` 外键关联用户，包含 `task_id` 唯一索引、`user_id` 索引和 `(user_id, status, created_at)` 联合索引。
- `agent_messages`：按业务 `task_id` 记录对话消息。
- `agent_tool_calls`：按业务 `task_id` 记录工具调用，`tool_args` 与 `tool_result` 使用 PostgreSQL `JSONB`。

可在 PostgreSQL 容器中确认表和索引：

```powershell
docker compose exec postgres psql -U postgres -d agent_task_db -c "\dt"
docker compose exec postgres psql -U postgres -d agent_task_db -c "\d agent_tasks"
```

### Session 生命周期与事务边界

`app/db/session.py` 中的 `get_db()` 是 FastAPI 的 `yield` 依赖。每次请求获得一个独立的 `Session`：业务正常结束时由 Service 层决定 `commit()`；请求抛出异常时依赖执行 `rollback()`；无论成功或失败都会 `close()`。

Repository 从参数接收 `Session`，不引用全局 Session。这样一个 Service 能把“创建任务”和“创建首条消息”放在同一事务中；第三阶段中任一步失败时回滚，避免只写入半份数据。

### ForeignKey 与 relationship

`ForeignKey("users.id")` 是 PostgreSQL 的数据库约束，它保证 `agent_tasks.user_id` 指向真实用户。`relationship()` 是 SQLAlchemy 在 Python 中提供的对象导航：`user.tasks` 与 `task.user` 方便读写关联对象，但不会替代数据库外键。

消息和工具调用采用对外业务 ID `task_id` 查询，便于后续接口直接按任务 ID 获取记录；当前需求没有为它们增加数据库外键。

### 6. 启动 FastAPI

```bash
uvicorn app.main:app --reload
```

- 健康检查：<http://127.0.0.1:8000/health>
- Swagger：<http://127.0.0.1:8000/docs>
- OpenAPI JSON：<http://127.0.0.1:8000/openapi.json>

## 当前可用接口

```text
GET /health
```

响应：

```json
{
  "status": "ok"
}
```

业务路由将在第三阶段实现，并统一位于 `/api/v1` 下。

## 请求日志与 request_id

请求中间件会优先读取 `X-Request-ID`；请求没有该 Header 时生成 UUID。每条访问日志包含 method、path、status_code、cost 和 request_id，响应中会返回：

```text
X-Request-ID: ...
X-Process-Time: ...
```

## 后续将补充的核心说明

第三、四阶段会继续加入：

- FastAPI BackgroundTasks 的适用范围与生产限制
- Agent 任务的原子状态更新与取消竞争处理
- PostgreSQL 索引与 `EXPLAIN ANALYZE` 学习示例
- 全部认证、任务、消息、工具调用和 SSE 接口

完整学习顺序参见 [LEARNING_PATH.md](LEARNING_PATH.md)。

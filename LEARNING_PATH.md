# AI Agent Task Platform 中文学习路线

这份路线不要求你一次理解所有文件。建议始终围绕一条真实调用链学习：**HTTP 请求进入 FastAPI，经过依赖注入和业务层，写入 PostgreSQL，再转换成 Pydantic 响应。**

## 第 0 站：先把项目跑起来

目标：先建立“代码确实能工作”的反馈，再阅读细节。

1. 创建虚拟环境并安装依赖。
2. 从 `.env.example` 复制 `.env`。
3. 执行 `uvicorn app.main:app --reload`。
4. 打开 `/health` 和 `/docs`。
5. 请求 `/health` 时自定义 `X-Request-ID`，观察响应 Header 和控制台日志。

重点文件：

- `app/main.py`：应用从哪里创建，组件如何注册。
- `app/core/config.py`：环境变量如何变成带类型的 Python 配置。
- `app/middlewares/request_context.py`：一个请求如何被中间件包裹。

## 第 1 站：理解 Python 工程结构和类型注解

目标：理解为什么不把所有代码放进 `main.py`。

- `api` 只处理 HTTP 协议。
- `schemas` 描述输入输出数据。
- `services` 表达业务规则。
- `repositories` 封装数据库访问。
- `db` 管理 ORM 模型与 Session。
- `core` 放横跨所有模块的配置、安全、日志和异常。

阅读函数签名中的 `str`、`dict[str, str]`、返回类型和 Pydantic 字段约束。类型注解主要服务于可读性、编辑器检查和静态分析，不会自动替代运行时验证；Pydantic 才负责接口数据的运行时验证。

## 第 2 站：理解 FastAPI 请求链

目标：能够口述一次请求经过哪些组件。

```text
客户端
  -> RequestContextMiddleware
  -> APIRouter
  -> Depends(get_db / get_current_user)
  -> Service
  -> Repository
  -> SQLAlchemy Session
  -> PostgreSQL
  -> Pydantic Response
  -> Middleware 添加响应 Header
  -> 客户端
```

第三阶段完成后，选取 `POST /api/v1/agent/tasks`，从路由开始逐层追踪，不要一开始横向读完所有文件。

## 第 3 站：理解数据库模型和 Session

目标：区分“Python 对象关系”和“数据库约束”。

- `ForeignKey` 是数据库约束，保护数据引用完整性。
- `relationship` 是 ORM 提供的 Python 对象导航能力，本身不会替代外键。
- Session 是一组数据库操作的工作单元，不等同于数据库连接。
- `flush` 把 SQL 发给数据库但不结束事务；`commit` 提交；`rollback` 撤销当前事务。
- FastAPI 的 yield 依赖会在响应结束时进入清理阶段并关闭 Session。

重点练习：人为让“创建任务后的消息写入”失败，确认任务也没有被提交，从而理解原子事务。

## 第 4 站：理解认证与依赖注入

目标：理解 JWT 解决了什么、没有解决什么。

1. 注册时只保存 bcrypt 密码哈希。
2. 登录时校验密码并签发带过期时间的 JWT。
3. `get_current_user()` 从 Bearer Token 解码身份。
4. 业务接口通过 `Depends` 获得当前用户。
5. 查询任务时仍要校验资源归属；“已经登录”不代表“可以访问所有任务”。

不要把敏感信息放进 JWT。JWT 默认只是签名而非加密，客户端能够读取载荷。

## 第 5 站：理解并发安全和后台任务

目标：理解“先查询再更新”为何可能重复运行任务。

两个请求可能同时读到 `created`。因此运行接口会使用类似下面的原子更新：

```sql
UPDATE agent_tasks
SET status = 'running'
WHERE task_id = :task_id
  AND status = 'created';
```

只有一个请求能影响一行，另一个请求得到 0 行并返回状态冲突。后台任务发生在 HTTP 响应之后，必须创建自己的 Session，不能继续使用请求依赖提供的 Session。

取消运行中任务时，模拟工作完成前还要重新检查状态，避免把 `cancelled` 覆盖成 `success`。

## 第 6 站：理解 SSE 与流式响应

目标：区分普通 JSON 响应和逐块传输。

SSE 使用 `text/event-stream`，服务端以 `data: ...\n\n` 逐条发送事件。学习时关注：

- async generator 如何逐步 yield 数据。
- 客户端断开后生成器如何结束。
- 为什么最终发送 `[DONE]` 是应用协议约定，而不是 SSE 标准强制要求。

## 第 7 站：理解迁移、索引和 EXPLAIN

目标：从“能查询”走向“知道查询成本”。

- Alembic migration 是数据库结构的版本历史，可审核、可升级、可回滚。
- 索引并非越多越好；它提高读取速度，也增加写入与存储成本。
- 使用 `EXPLAIN ANALYZE` 对比用户任务列表有无状态筛选时的执行计划。
- 重点观察 `Seq Scan`、`Index Scan`、估算 Rows、实际 Rows、Planning Time 和 Execution Time。

## 建议练习顺序

1. 修改应用名称，观察配置变化。
2. 携带与不携带 `X-Request-ID` 请求 `/health`。
3. 完成迁移后，用 SQL 查看四张表和索引。
4. 注册、登录、调用 `/me`，手动解码 JWT 载荷。
5. 创建任务并核对任务与 user message 是否同时存在。
6. 并发调用两次 run，确认只有一次成功抢占。
7. 运行后立即 cancel，确认后台任务不会覆盖取消状态。
8. 使用 `curl -N` 观察 SSE 数据逐条到达。
9. 执行 README 中的 `EXPLAIN ANALYZE`，对照索引理解执行计划。

每完成一站，都尝试回答三个问题：请求从哪里进入、状态在哪里改变、失败后如何恢复。能回答这三个问题，就不只是“看懂代码”，而是开始理解后端系统的运行方式。

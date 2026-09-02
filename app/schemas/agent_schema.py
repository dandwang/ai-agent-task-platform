"""Agent 任务、消息与工具调用接口的 Pydantic 模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateAgentTaskRequest(BaseModel):
    """创建 Agent 任务请求。"""

    prompt: str = Field(min_length=1, max_length=10_000)
    priority: int = Field(default=0, ge=0, le=10)


class AgentTaskResponse(BaseModel):
    """任务公开响应。"""

    model_config = ConfigDict(from_attributes=True)

    task_id: str
    prompt: str
    status: str
    answer: str | None
    error_code: str | None
    error_message: str | None
    retry_count: int
    priority: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class AgentTaskListResponse(BaseModel):
    """当前用户任务列表响应。"""

    items: list[AgentTaskResponse]
    total: int


class AgentMessageResponse(BaseModel):
    """任务消息响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: str
    role: str
    content: str
    created_at: datetime


class AgentToolCallResponse(BaseModel):
    """任务工具调用响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: str
    tool_name: str
    tool_args: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    status: str
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

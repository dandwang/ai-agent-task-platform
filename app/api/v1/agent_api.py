from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.agent_schema import (
    AgentMessageResponse,
    AgentTaskListResponse,
    AgentTaskResponse,
    AgentToolCallResponse,
    CreateAgentTaskRequest,
)
from app.services.agent_task_service import AgentTaskService, run_task_in_background

router = APIRouter()
agent_task_service = AgentTaskService()


@router.post("/tasks", response_model=AgentTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    request: CreateAgentTaskRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTaskResponse:
    """创建任务及其第一条 user message。"""
    task = agent_task_service.create_task(session, current_user, request)
    return AgentTaskResponse.model_validate(task)


@router.get("/tasks", response_model=AgentTaskListResponse)
def list_tasks(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTaskListResponse:
    """查询当前用户的任务列表。"""
    tasks = agent_task_service.list_tasks(session, current_user)
    items = [AgentTaskResponse.model_validate(task) for task in tasks]
    return AgentTaskListResponse(items=items, total=len(items))


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
def get_task(
    task_id: str,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTaskResponse:
    """查询当前用户拥有的一项任务。"""
    task = agent_task_service.get_task(session, current_user, task_id)
    return AgentTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/run", response_model=AgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def run_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTaskResponse:
    """抢占任务并在 HTTP 响应后启动轻量后台模拟执行。"""
    task = agent_task_service.start_task(session, current_user, task_id)
    background_tasks.add_task(run_task_in_background, task.task_id, current_user.id)
    return AgentTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/cancel", response_model=AgentTaskResponse)
def cancel_task(
    task_id: str,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentTaskResponse:
    """取消 created 或 running 状态的当前用户任务。"""
    task = agent_task_service.cancel_task(session, current_user, task_id)
    return AgentTaskResponse.model_validate(task)


@router.get("/tasks/{task_id}/messages", response_model=list[AgentMessageResponse])
def list_messages(
    task_id: str,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AgentMessageResponse]:
    """查询当前用户任务的消息记录。"""
    messages = agent_task_service.list_messages(session, current_user, task_id)
    return [AgentMessageResponse.model_validate(message) for message in messages]


@router.get("/tasks/{task_id}/tool-calls", response_model=list[AgentToolCallResponse])
def list_tool_calls(
    task_id: str,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AgentToolCallResponse]:
    """查询当前用户任务的工具调用记录。"""
    tool_calls = agent_task_service.list_tool_calls(session, current_user, task_id)
    return [AgentToolCallResponse.model_validate(tool_call) for tool_call in tool_calls]

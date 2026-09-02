"""Agent 任务生命周期、事务和后台模拟执行逻辑。"""

from datetime import datetime
import logging
import time
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvalidTaskStatusError,
    TaskNotFoundError,
    TaskPermissionDeniedError,
)
from app.db.models import AgentMessage, AgentTask, AgentToolCall, User
from app.db.session import SessionLocal
from app.repositories.agent_message_repository import AgentMessageRepository
from app.repositories.agent_task_repository import AgentTaskRepository
from app.repositories.agent_tool_call_repository import AgentToolCallRepository
from app.schemas.agent_schema import CreateAgentTaskRequest

logger = logging.getLogger(__name__)

TASK_STATUS_CREATED = "created"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCESS = "success"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_CANCELLED = "cancelled"


class AgentTaskService:
    """任务业务层：资源归属、事务和状态机规则都在此处集中管理。"""

    def __init__(
        self,
        task_repository: AgentTaskRepository | None = None,
        message_repository: AgentMessageRepository | None = None,
        tool_call_repository: AgentToolCallRepository | None = None,
    ) -> None:
        self.task_repository = task_repository or AgentTaskRepository()
        self.message_repository = message_repository or AgentMessageRepository()
        self.tool_call_repository = tool_call_repository or AgentToolCallRepository()

    def create_task(
        self, session: Session, user: User, request: CreateAgentTaskRequest
    ) -> AgentTask:
        """在同一事务写入任务及其第一条 user message。"""
        task_id = uuid4().hex
        task = AgentTask(
            task_id=task_id,
            user_id=user.id,
            prompt=request.prompt,
            priority=request.priority,
            status=TASK_STATUS_CREATED,
        )
        message = AgentMessage(task_id=task_id, role="user", content=request.prompt)
        try:
            self.task_repository.add(session, task)
            self.message_repository.add(session, message)
            session.commit()
            session.refresh(task)
        except Exception:
            session.rollback()
            raise
        return task

    def list_tasks(self, session: Session, user: User) -> list[AgentTask]:
        """返回当前用户自己的任务列表。"""
        return self.task_repository.list_by_user_id(session, user.id)

    def get_task(self, session: Session, user: User, task_id: str) -> AgentTask:
        """查询任务并检查资源归属。"""
        task = self.task_repository.get_by_task_id(session, task_id)
        if task is None:
            raise TaskNotFoundError()
        if task.user_id != user.id:
            raise TaskPermissionDeniedError()
        return task

    def list_messages(
        self, session: Session, user: User, task_id: str
    ) -> list[AgentMessage]:
        """确认归属后返回任务消息。"""
        self.get_task(session, user, task_id)
        return self.message_repository.list_by_task_id(session, task_id)

    def list_tool_calls(
        self, session: Session, user: User, task_id: str
    ) -> list[AgentToolCall]:
        """确认归属后返回任务工具调用。"""
        self.get_task(session, user, task_id)
        return self.tool_call_repository.list_by_task_id(session, task_id)

    def start_task(self, session: Session, user: User, task_id: str) -> AgentTask:
        """原子抢占 created 任务，避免并发请求重复开始同一任务。"""
        self.get_task(session, user, task_id)
        task = self.task_repository.claim_for_run(session, task_id, user.id, datetime.now())
        if task is None:
            session.rollback()
            raise InvalidTaskStatusError("只有 created 状态的任务可以运行")
        session.commit()
        return task

    def cancel_task(self, session: Session, user: User, task_id: str) -> AgentTask:
        """原子取消 created 或 running 任务，其他状态不允许取消。"""
        self.get_task(session, user, task_id)
        task = self.task_repository.cancel_if_allowed(session, task_id, user.id, datetime.now())
        if task is None:
            session.rollback()
            raise InvalidTaskStatusError("只有 created 或 running 状态的任务可以取消")
        session.commit()
        return task


def run_task_in_background(task_id: str, user_id: int) -> None:
    """模拟任务执行；后台函数创建独立 Session，不能复用请求 Session。"""
    session = SessionLocal()
    service = AgentTaskService()
    try:
        # 此处预留真实 LLM / httpx 调用位置；当前仅模拟少量耗时。
        time.sleep(2)
        task = service.task_repository.get_by_task_id(session, task_id)
        if task is None or task.user_id != user_id or task.status != TASK_STATUS_RUNNING:
            return

        now = datetime.now()
        answer = f"模拟分析完成：已处理你的任务“{task.prompt}”。"
        tool_call = AgentToolCall(
            task_id=task_id,
            tool_name="mock_search_tool",
            tool_args={"query": task.prompt},
            tool_result={"summary": "这是模拟工具返回结果"},
            status=TASK_STATUS_SUCCESS,
            started_at=now,
            finished_at=now,
        )
        message = AgentMessage(task_id=task_id, role="assistant", content=answer)
        service.tool_call_repository.add(session, tool_call)
        service.message_repository.add(session, message)

        # 最终状态更新也附带 running 条件；cancel 抢先提交时会回滚本次结果写入。
        if not service.task_repository.mark_success_if_running(
            session, task_id, user_id, answer, now
        ):
            session.rollback()
            return
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception("模拟任务执行失败 task_id=%s", task_id)
        try:
            if service.task_repository.mark_failed_if_running(
                session, task_id, user_id, str(exc), datetime.now()
            ):
                session.commit()
            else:
                session.rollback()
        except Exception:
            session.rollback()
            logger.exception("记录任务失败状态失败 task_id=%s", task_id)
    finally:
        session.close()

"""Agent 任务表的数据访问封装。"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import AgentTask


class AgentTaskRepository:
    """封装任务的查询与写入，不承担 HTTP 或业务状态规则。"""

    def get_by_task_id(self, session: Session, task_id: str) -> AgentTask | None:
        """按对外业务 ID 查询任务。"""
        return session.scalar(select(AgentTask).where(AgentTask.task_id == task_id))

    def list_by_user_id(self, session: Session, user_id: int) -> list[AgentTask]:
        """按创建时间倒序返回用户的全部任务。"""
        statement = (
            select(AgentTask)
            .where(AgentTask.user_id == user_id)
            .order_by(AgentTask.created_at.desc())
        )
        return list(session.scalars(statement))

    def add(self, session: Session, task: AgentTask) -> None:
        """将任务加入当前事务。"""
        session.add(task)

    def claim_for_run(
        self, session: Session, task_id: str, user_id: int, started_at: datetime
    ) -> AgentTask | None:
        """仅将 created 任务原子变更为 running，防止重复执行。"""
        statement = (
            update(AgentTask)
            .where(
                AgentTask.task_id == task_id,
                AgentTask.user_id == user_id,
                AgentTask.status == "created",
            )
            .values(status="running", started_at=started_at, updated_at=started_at)
            .returning(AgentTask)
        )
        return session.scalar(statement)

    def cancel_if_allowed(
        self, session: Session, task_id: str, user_id: int, finished_at: datetime
    ) -> AgentTask | None:
        """仅将 created 或 running 任务原子变更为 cancelled。"""
        statement = (
            update(AgentTask)
            .where(
                AgentTask.task_id == task_id,
                AgentTask.user_id == user_id,
                AgentTask.status.in_(("created", "running")),
            )
            .values(status="cancelled", finished_at=finished_at, updated_at=finished_at)
            .returning(AgentTask)
        )
        return session.scalar(statement)

    def mark_success_if_running(
        self,
        session: Session,
        task_id: str,
        user_id: int,
        answer: str,
        finished_at: datetime,
    ) -> bool:
        """只有尚在 running 状态时才写入成功结果，避免覆盖取消状态。"""
        statement = (
            update(AgentTask)
            .where(
                AgentTask.task_id == task_id,
                AgentTask.user_id == user_id,
                AgentTask.status == "running",
            )
            .values(
                status="success",
                answer=answer,
                finished_at=finished_at,
                updated_at=finished_at,
            )
        )
        return session.execute(statement).rowcount == 1

    def mark_failed_if_running(
        self,
        session: Session,
        task_id: str,
        user_id: int,
        error_message: str,
        finished_at: datetime,
    ) -> bool:
        """仅标记尚未取消的运行中任务为失败。"""
        statement = (
            update(AgentTask)
            .where(
                AgentTask.task_id == task_id,
                AgentTask.user_id == user_id,
                AgentTask.status == "running",
            )
            .values(
                status="failed",
                error_code="TASK_EXECUTION_FAILED",
                error_message=error_message,
                finished_at=finished_at,
                updated_at=finished_at,
            )
        )
        return session.execute(statement).rowcount == 1

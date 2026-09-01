"""Agent 任务表的数据访问封装。"""

from sqlalchemy import select
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

"""Agent 消息表的数据访问封装。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentMessage


class AgentMessageRepository:
    """按业务 task_id 管理消息记录。"""

    def list_by_task_id(self, session: Session, task_id: str) -> list[AgentMessage]:
        """按写入顺序返回一项任务的消息。"""
        statement = (
            select(AgentMessage)
            .where(AgentMessage.task_id == task_id)
            .order_by(AgentMessage.created_at.asc(), AgentMessage.id.asc())
        )
        return list(session.scalars(statement))

    def add(self, session: Session, message: AgentMessage) -> None:
        """将消息加入当前事务。"""
        session.add(message)

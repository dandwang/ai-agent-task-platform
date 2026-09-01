"""Agent 工具调用表的数据访问封装。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentToolCall


class AgentToolCallRepository:
    """按业务 task_id 管理工具调用记录。"""

    def list_by_task_id(self, session: Session, task_id: str) -> list[AgentToolCall]:
        """按写入顺序返回一项任务的工具调用。"""
        statement = (
            select(AgentToolCall)
            .where(AgentToolCall.task_id == task_id)
            .order_by(AgentToolCall.created_at.asc(), AgentToolCall.id.asc())
        )
        return list(session.scalars(statement))

    def add(self, session: Session, tool_call: AgentToolCall) -> None:
        """将工具调用加入当前事务。"""
        session.add(tool_call)

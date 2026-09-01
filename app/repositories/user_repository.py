"""用户表的数据访问封装。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


class UserRepository:
    """只负责用户查询与持久化，不处理密码或事务规则。"""

    def get_by_id(self, session: Session, user_id: int) -> User | None:
        """按主键查询用户。"""
        return session.scalar(select(User).where(User.id == user_id))

    def get_by_username(self, session: Session, username: str) -> User | None:
        """按唯一用户名查询用户。"""
        return session.scalar(select(User).where(User.username == username))

    def add(self, session: Session, user: User) -> None:
        """将用户加入当前事务，提交由 Service 层决定。"""
        session.add(user)

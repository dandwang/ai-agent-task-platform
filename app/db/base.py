"""SQLAlchemy 声明式模型的公共基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型共享的元数据入口，供 Alembic 发现表结构。"""


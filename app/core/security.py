"""密码哈希、JWT 与当前用户依赖。"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import InvalidCredentialsError
from app.db.models import User
from app.db.session import get_db
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)
user_repository = UserRepository()


def hash_password(password: str) -> str:
    """生成 bcrypt 密码哈希，明文密码不进入数据库。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码是否匹配已保存的 bcrypt 哈希。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: User) -> str:
    """创建包含用户身份和过期时间的 JWT access token。"""
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    """解析 Bearer Token，并从数据库返回仍然有效的当前用户。"""
    if credentials is None:
        raise InvalidCredentialsError()

    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("user_id")
        username = payload.get("username")
        if not isinstance(user_id, int) or not isinstance(username, str):
            raise InvalidCredentialsError()
    except jwt.PyJWTError as exc:
        raise InvalidCredentialsError() from exc

    user = user_repository.get_by_id(session, user_id)
    if user is None or not user.is_active or user.username != username:
        raise InvalidCredentialsError()
    return user

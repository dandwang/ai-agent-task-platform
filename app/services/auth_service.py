"""注册、登录与当前用户查询的业务规则。"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    """认证业务层，负责密码安全与用户写入事务。"""

    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def register(self, session: Session, request: RegisterRequest) -> User:
        """注册用户；用户名冲突或写入失败时回滚整个事务。"""
        if self.user_repository.get_by_username(session, request.username) is not None:
            raise UserAlreadyExistsError()

        user = User(
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
        )
        try:
            self.user_repository.add(session, user)
            session.commit()
            session.refresh(user)
        except IntegrityError as exc:
            session.rollback()
            raise UserAlreadyExistsError() from exc
        except Exception:
            session.rollback()
            raise
        return user

    def login(self, session: Session, request: LoginRequest) -> TokenResponse:
        """校验凭据并签发 access token。"""
        user = self.user_repository.get_by_username(session, request.username)
        if user is None or not user.is_active:
            raise InvalidCredentialsError()
        if not verify_password(request.password, user.password_hash):
            raise InvalidCredentialsError()
        return TokenResponse(access_token=create_access_token(user))

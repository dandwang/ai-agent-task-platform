from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth_schema import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()


@router.post("/register", response_model=CurrentUserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest, session: Annotated[Session, Depends(get_db)]
) -> User:
    """注册新用户。"""
    return auth_service.register(session, request)


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest, session: Annotated[Session, Depends(get_db)]
) -> TokenResponse:
    """校验用户名和密码，返回 Bearer Token。"""
    return auth_service.login(session, request)


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """返回当前 Bearer Token 对应的用户信息。"""
    return current_user

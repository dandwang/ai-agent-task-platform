from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@dataclass
class AppError(Exception):
    """所有可预期业务异常的基类。"""

    code: str
    message: str
    status_code: int


class UserAlreadyExistsError(AppError):
    def __init__(self) -> None:
        super().__init__("USER_ALREADY_EXISTS", "用户名已存在", 409)


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__("INVALID_CREDENTIALS", "用户名或密码错误", 401)


class UserNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__("USER_NOT_FOUND", "用户不存在", 404)


class TaskNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__("TASK_NOT_FOUND", "任务不存在", 404)


class TaskPermissionDeniedError(AppError):
    def __init__(self) -> None:
        super().__init__("TASK_PERMISSION_DENIED", "无权访问该任务", 403)


class InvalidTaskStatusError(AppError):
    def __init__(self, message: str = "当前任务状态不允许此操作") -> None:
        super().__init__("INVALID_TASK_STATUS", message, 409)


def register_exception_handlers(app: FastAPI) -> None:
    """把业务异常转换为统一的 HTTP 响应结构。"""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            },
        )

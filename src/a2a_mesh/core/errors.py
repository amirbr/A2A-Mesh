"""Typed HTTP exceptions that produce the standard error response format."""

from fastapi import HTTPException, status


def _body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


class AuthError(HTTPException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=_body("auth_required", message))


class ForbiddenError(HTTPException):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=_body("forbidden", message))


class NotFoundError(HTTPException):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_body("not_found", f"{resource} not found"),
        )


class ConflictError(HTTPException):
    def __init__(self, message: str = "Already exists") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=_body("conflict", message))


class ValidationError(HTTPException):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_body("validation_error", message, details),
        )

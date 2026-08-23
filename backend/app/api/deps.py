"""FastAPI dependencies: DB session, auth, RBAC and pagination."""
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Role capability sets (plan §21/§24)
STAFF_ROLES: set[UserRole] = {UserRole.ADMIN, UserRole.EDITOR, UserRole.MODERATOR}
WRITE_ROLES: set[UserRole] = {UserRole.ADMIN, UserRole.EDITOR}
PUBLISH_ROLES: set[UserRole] = {UserRole.ADMIN, UserRole.EDITOR, UserRole.MODERATOR}
ADMIN_ROLES: set[UserRole] = {UserRole.ADMIN}

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user_optional(
    db: DbSession,
    token: str | None = Depends(oauth2_scheme),
) -> User | None:
    """Resolve the user from the bearer token; None for anonymous calls."""
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except HTTPException:
        return None
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Required-auth variant."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="يجب تسجيل الدخول للمتابعة",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: UserRole):
    """Dependency factory enforcing role-based access."""

    def _checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ليست لديك صلاحية تنفيذ هذا الإجراء",
            )
        return user

    return _checker


StaffUser = Annotated[User, Depends(require_roles(*STAFF_ROLES))]
WriterUser = Annotated[User, Depends(require_roles(*WRITE_ROLES))]
PublisherUser = Annotated[User, Depends(require_roles(*PUBLISH_ROLES))]
AdminUser = Annotated[User, Depends(require_roles(*ADMIN_ROLES))]


class PaginationParams:
    """Common page/page_size query parameters with sane bounds."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, le=10_000)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 12,
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


Pagination = Annotated[PaginationParams, Depends()]


def paginate_response(items, total: int, pagination: PaginationParams):
    from app.schemas.common import PageMeta

    pages = max(1, -(-total // pagination.page_size))
    meta = PageMeta(
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        pages=pages,
    )
    return {"items": items, "meta": meta.model_dump()}


def request_meta(request: Request) -> tuple[str | None, str | None]:
    """Return (client_ip, user_agent) for view tracking."""
    from app.core.ratelimit import client_ip

    return client_ip(request), request.headers.get("user-agent")

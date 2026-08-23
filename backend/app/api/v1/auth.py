"""Authentication endpoints: login, refresh, me, logout."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.core.ratelimit import rate_limit
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import RefreshRequest, TokenPair, UserOut
from app.services.audit import AuditAction, log_action

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user: User) -> TokenPair:
    from app.core.config import get_settings

    expires = get_settings().access_token_expire_minutes * 60
    return TokenPair(
        access_token=create_access_token(user.id, user.username, user.role.value),
        refresh_token=create_refresh_token(user.id),
        expires_in=expires,
    )


@router.post("/login", response_model=ApiResponse[TokenPair])
def login(
    request: Request,
    db: DbSession,
    form: OAuth2PasswordRequestForm = Depends(),
) -> ApiResponse[TokenPair]:
    """OAuth2 password flow used by the desktop admin and Swagger UI."""
    rate_limit(request, "login", per_minute=10)

    user = db.query(User).filter(User.username == form.username).first()
    if user is None:
        # Constant-ish time path to avoid trivial username enumeration.
        from app.core.security import hash_password

        hash_password(form.password)

    if user is None or not user.is_active or not _verify(user.password_hash, form.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة المرور غير صحيحة",
        )

    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    log_action(db, user_id=user.id, action=AuditAction.LOGIN, entity_type="user", entity_id=user.id)

    tokens = _issue_tokens(user)
    return ApiResponse(message="تم تسجيل الدخول بنجاح", data=tokens)


def _verify(hashed: str, plain: str) -> bool:
    from app.core.security import verify_password

    return verify_password(plain, hashed)


@router.post("/refresh", response_model=ApiResponse[TokenPair])
def refresh(body: RefreshRequest, db: DbSession) -> ApiResponse[TokenPair]:
    """Exchange a valid refresh token for a fresh token pair."""
    payload = decode_token(body.refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="حساب غير متاح")
    return ApiResponse(data=_issue_tokens(user))


@router.get("/me", response_model=ApiResponse[UserOut])
def me(current_user: CurrentUser) -> ApiResponse[UserOut]:
    """Profile of the authenticated user."""
    return ApiResponse(data=UserOut.model_validate(current_user))


@router.post("/logout", response_model=ApiResponse[None])
def logout(current_user: CurrentUser, db: DbSession) -> ApiResponse[None]:
    """Stateless JWT logout — client discards tokens; we audit the event."""
    log_action(db, user_id=current_user.id, action=AuditAction.LOGOUT, entity_type="user", entity_id=current_user.id)
    return ApiResponse(message="تم تسجيل الخروج")

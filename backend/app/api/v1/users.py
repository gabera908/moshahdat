"""User management (admin only)."""
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import AdminUser, CurrentUser, DbSession, Pagination
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.user import PasswordReset, UserCreate, UserOut, UserUpdate
from app.services.audit import AuditAction, log_action

router = APIRouter(prefix="/users", tags=["users"])


def _serialize(user: User) -> UserOut:
    return UserOut.model_validate(user)


def _get_or_404(db: DbSession, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    return user


@router.get("")
def list_users(
    db: DbSession,
    pagination: Pagination,
    _admin: AdminUser,
    q: str | None = Query(default=None, max_length=100),
) -> dict:
    """Search + paginate users. Returns {items, meta} envelope."""
    query = db.query(User)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            User.username.ilike(like) | User.email.ilike(like) | User.full_name.ilike(like)
        )
    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    from app.api.deps import paginate_response

    data = paginate_response([_serialize(u).model_dump(mode="json") for u in users], total, pagination)
    return {"success": True, "message": "", "data": data}


@router.get("/count")
def count_users(db: DbSession, _admin: AdminUser) -> dict:
    return {"success": True, "data": {"total": db.query(User).count()}}


@router.post("", response_model=ApiResponse[UserOut], status_code=201)
def create_user(
    payload: UserCreate,
    db: DbSession,
    admin: AdminUser,
) -> ApiResponse[UserOut]:
    if db.query(User.id).filter((User.username == payload.username) | (User.email == str(payload.email))).first():
        raise HTTPException(status_code=409, detail="اسم المستخدم أو البريد مستخدم مسبقًا")

    user = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    log_action(db, user_id=admin.id, action=AuditAction.CREATE, entity_type="user", entity_id=user.id,
               details={"username": user.username})
    return ApiResponse(message="تم إنشاء المستخدم", data=_serialize(user))


@router.get("/{user_id}", response_model=ApiResponse[UserOut])
def get_user(user_id: int, db: DbSession, _admin: AdminUser) -> ApiResponse[UserOut]:
    return ApiResponse(data=_serialize(_get_or_404(db, user_id)))


@router.put("/{user_id}", response_model=ApiResponse[UserOut])
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DbSession,
    admin: AdminUser,
) -> ApiResponse[UserOut]:
    user = _get_or_404(db, user_id)

    # Safety rails around role/active changes on the last active admin.
    if user.role == UserRole.ADMIN:
        other_admins = (
            db.query(User.id).filter(User.role == UserRole.ADMIN, User.id != user.id, User.is_active.is_(True)).count()
        )
        demoting_or_disabling = (
            (payload.role is not None and payload.role != UserRole.ADMIN)
            or (payload.is_active is False)
        )
        if demoting_or_disabling and other_admins == 0:
            raise HTTPException(status_code=409, detail="لا يمكن إزالة آخر مدير نشط في النظام")

    if payload.email is not None:
        clash = db.query(User.id).filter(User.email == str(payload.email), User.id != user.id).first()
        if clash:
            raise HTTPException(status_code=409, detail="البريد مستخدم مسبقًا")
        user.email = str(payload.email)
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    log_action(db, user_id=admin.id, action=AuditAction.UPDATE, entity_type="user", entity_id=user.id)
    return ApiResponse(message="تم تحديث المستخدم", data=_serialize(user))


@router.patch("/{user_id}/password", response_model=ApiResponse[None])
def reset_password(
    user_id: int,
    body: PasswordReset,
    db: DbSession,
    admin: AdminUser,
) -> ApiResponse[None]:
    user = _get_or_404(db, user_id)
    user.password_hash = hash_password(body.new_password)
    log_action(db, user_id=admin.id, action=AuditAction.UPDATE, entity_type="user",
               entity_id=user.id, details={"action": "password_reset"})
    return ApiResponse(message="تم تعيين كلمة مرور جديدة")


@router.delete("/{user_id}", response_model=ApiResponse[None])
def delete_user(user_id: int, db: DbSession, admin: AdminUser) -> ApiResponse[None]:
    user = _get_or_404(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=409, detail="لا يمكنك حذف حسابك الحالي")
    if user.role == UserRole.ADMIN and (
        db.query(User.id).filter(User.role == UserRole.ADMIN, User.id != user.id).count() == 0
    ):
        raise HTTPException(status_code=409, detail="لا يمكن حذف آخر مدير في النظام")

    db.delete(user)
    log_action(db, user_id=admin.id, action=AuditAction.DELETE, entity_type="user", entity_id=user_id,
               details={"username": user.username})
    return ApiResponse(message="تم حذف المستخدم")

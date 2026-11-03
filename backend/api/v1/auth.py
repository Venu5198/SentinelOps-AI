import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.core.rbac import AuthenticatedUser, get_current_user
from backend.core.security import create_access_token, get_password_hash, verify_password
from backend.db.mongodb import get_database
from backend.models.user import TokenResponse, UserCreate, UserLogin, UserResponse
from backend.services.audit_service import record_audit_log

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, request: Request):
    db = get_database()
    existing = await db.users.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"User with email '{user_in.email}' already exists"
        )
    user_id = f"user_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    user_doc = {
        "_id": user_id,
        "email": user_in.email,
        "password_hash": get_password_hash(user_in.password),
        "role": user_in.role.value,
        "is_active": True,
        "created_at": now,
    }
    await db.users.insert_one(user_doc)

    await record_audit_log(
        actor_id=user_id,
        actor_role=user_in.role.value,
        action="USER_REGISTERED",
        resource_type="user",
        resource_id=user_id,
        request_ip=request.client.host if request.client else None,
    )

    return UserResponse(**user_doc)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    db = get_database()
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        await record_audit_log(
            actor_id="anonymous",
            actor_role="anonymous",
            action="LOGIN_FAILED",
            resource_type="user",
            resource_id=credentials.email,
            result="failure",
            request_ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(data={"sub": user["_id"], "email": user["email"], "role": user["role"]})

    await record_audit_log(
        actor_id=user["_id"],
        actor_role=user["role"],
        action="LOGIN_SUCCESS",
        resource_type="user",
        resource_id=user["_id"],
        request_ip=request.client.host if request.client else None,
    )

    return TokenResponse(access_token=token, token_type="bearer", user=UserResponse(**user))


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    db = get_database()
    user = await db.users.find_one({"_id": current_user.user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(**user)

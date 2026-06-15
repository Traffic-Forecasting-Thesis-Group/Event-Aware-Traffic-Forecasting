from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from .database import get_db_session
from .models import User
from .auth_utils import hash_password, verify_password, create_access_token
from .auth_deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────────

class RegisterPayload(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class AuthTokenResponse(BaseModel):
    accessToken: str


class ForgotPasswordPayload(BaseModel):
    email: EmailStr


class VerifyCodePayload(BaseModel):
    email: EmailStr
    code: str


class ResetPasswordPayload(BaseModel):
    email: EmailStr
    code: str
    newPassword: str


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthTokenResponse)
async def register(payload: RegisterPayload, db: AsyncSession = Depends(get_db_session)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()

    token = create_access_token(subject=user.email)
    return AuthTokenResponse(accessToken=token)


@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: LoginPayload, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(subject=user.email)
    return AuthTokenResponse(accessToken=token)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # JWTs are stateless; logout is handled client-side by discarding the
    # token. If you later add a refresh-token/blocklist mechanism, revoke
    # it here.
    return {"status": "success"}


# ── Password reset (placeholder flow) ──────────────────────────────────
#
# NOTE: these three endpoints currently do NOT send real emails or persist
# reset codes anywhere. They exist so the frontend's ForgotPassword /
# VerificationCode / ResetPassword screens don't 404. Wire up an email
# provider + a reset_codes table (or Redis with TTL) before relying on
# this in production.

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None:
        # Don't reveal whether the email exists.
        return {"status": "success", "message": "If that email exists, a code has been sent."}

    # TODO: generate a real code, store it (Redis with TTL), email it.
    print(f"[forgot-password] would send reset code to {payload.email}")
    return {"status": "success", "message": "If that email exists, a code has been sent."}


@router.post("/verify-code")
async def verify_code(payload: VerifyCodePayload):
    # TODO: look up the stored code for payload.email and compare.
    print(f"[verify-code] verifying code for {payload.email}: {payload.code}")
    return {"status": "success"}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordPayload, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    # TODO: verify payload.code against the stored reset code before
    # allowing the password change.
    user.hashed_password = hash_password(payload.newPassword)
    await db.commit()
    return {"status": "success"}

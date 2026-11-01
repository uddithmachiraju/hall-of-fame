from fastapi import APIRouter, Depends, Query, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

import src.services.authentication.auth as auth_service
from src.db.mongo_db import get_db
from src.schemas.users import (
    UserLoginRequest,
    UserLoginResponse,
    UserRefreshTokenRequest,
    UserRefreshTokenResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)

router = APIRouter()


@router.post("/register", response_model=UserRegisterResponse, status_code=201)
async def register(payload: UserRegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """User registration endpoint."""

    response = await auth_service.register_user(payload, db)
    return response


@router.get("/verify-email", status_code=200)
async def verify_email(
    token: str = Query(..., description="The email verification token sent to the user's email."),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Email verification endpoint."""
    await auth_service.verify_email(token, db)


@router.post("/login", response_model=UserLoginResponse)
async def login(request: Request, payload: UserLoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """User login endpoint."""

    response = await auth_service.login_user(payload, request, db)
    return response


@router.post("/refresh-token", response_model=UserRefreshTokenResponse)
async def refresh_token(data: UserRefreshTokenRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Refresh JWT token endpoint."""

    response = await auth_service.refresh_token(data, db)
    return response


@router.post("/logout", response_model=dict, status_code=200)
async def logout(request: UserRefreshTokenRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """User logout endpoint."""

    return await auth_service.logout_user(request, db)

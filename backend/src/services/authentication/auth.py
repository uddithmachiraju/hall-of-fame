import asyncio
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import HTTPException, Request, status
from fastapi.responses import HTMLResponse
from jose import JWTError, jwt  # type: ignore
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext

from src.config.logging import get_logger
from src.config.settings import settings
from src.core.auth import create_refresh_token, create_user_token
from src.core.email import generate_token, hash_token, send_verification_email
from src.schemas.users import (
    UserLoginRequest,
    UserLoginResponse,
    UserRefreshTokenRequest,
    UserRefreshTokenResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
dummy_hash = pwd_context.hash("dummy-password-for-timing-attack-prevention")


def hash_password(password: str) -> str:
    """hash a plain text using bcrypt."""

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""

    return pwd_context.verify(plain_password, hashed_password)


async def _store_refresh_token(db: AsyncIOMotorDatabase, jti: str, user_id: str):
    """Store the refresh token in the database."""

    token_doc = {
        "jti": jti,
        "user_id": user_id,
        "issued_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "revoked": False,
        "replaced_by": None,
    }

    return db.refresh_tokens.insert_one(token_doc)


async def register_user(payload: UserRegisterRequest, db: AsyncIOMotorDatabase) -> UserRegisterResponse:
    """Registers a new user in the database."""

    # Check if the user already exists
    existing_user = await db.users.find_one({"email": payload.email})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists.")

    # Hash the password (you should implement a proper hashing mechanism)
    hashed_password = hash_password(payload.password)

    # Create the user document
    user_doc = {
        "username": payload.username,
        "full_name": payload.full_name,
        "email": payload.email,
        "password": hashed_password,
        "region_code": payload.region_code,
        "role": "user",
        "is_active": True,
        "is_email_verified": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    # Insert the user into the database
    result = await db.users.insert_one(user_doc)

    # Generate a verification token and send a verification email
    raw_token = generate_token()

    # Store the verification token in the database
    token_record = {
        "user_id": str(result.inserted_id),
        "token_hash": hash_token(raw_token),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS),
        "used_at": None,
    }

    await db.email_verification_tokens.insert_one(token_record)

    # send the verification email to the user
    send_verification_email(payload.email, payload.username, raw_token)
    logger.info("verification_email_sent", email=payload.email, username=payload.username)

    return UserRegisterResponse(
        id=str(result.inserted_id),
        username=payload.username,
        email=payload.email,
        is_active=True,
        is_email_verified=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


async def verify_email(token: str, db: AsyncIOMotorDatabase):
    """Verifies the user's email using the provided token."""

    # Hash the token to compare with the stored hash
    token_hash = hash_token(token)

    # Find the token record in the database
    token_record = await db.email_verification_tokens.find_one({"token_hash": token_hash})

    if not token_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token.")

    if token_record["used_at"] is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token has already been used.")

    if token_record["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token has expired.")

    # Mark the user email as verified
    await db.users.update_one(
        {"_id": ObjectId(token_record["user_id"])},
        {"$set": {"is_email_verified": True}},
    )

    # Mark the token as used
    await db.email_verification_tokens.update_one(
        {"_id": token_record["_id"]},
        {"$set": {"used_at": datetime.now(timezone.utc)}},
    )

    logger.info("email_verified", user_id=token_record["user_id"])

    return HTMLResponse(
        content="<h1>Email verified successfully!</h1><p>You can now log in to your account.</p>",
        status_code=status.HTTP_200_OK,
    )


async def login_user(payload: UserLoginRequest, request: Request, db: AsyncIOMotorDatabase) -> UserLoginResponse:
    """Authenticates a user and returns a JWT."""

    client_ip = request.client.host if request.client else "unknown"
    logger.info("login_attempt", email=payload.email, client_ip=client_ip)

    user = await db.users.find_one({"email": payload.email})

    password_valid = (
        await asyncio.to_thread(verify_password, payload.password, user["password"])
        if user
        else await asyncio.to_thread(verify_password, payload.password, dummy_hash)
    )

    if not user or not password_valid:
        logger.warning("login_failed", email=payload.email, client_ip=client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    if not user["is_email_verified"]:
        logger.warning("login_failed_email_not_verified", email=payload.email, client_ip=client_ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified.")

    if not user["is_active"]:
        logger.warning("login_failed_account_inactive", email=payload.email, client_ip=client_ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")

    token = create_user_token(user_id=str(user["_id"]), role=user["role"])
    refresh_token, jti = create_refresh_token(user_id=str(user["_id"]), role=user["role"])

    # Store the refresh token in the database
    asyncio.create_task(_store_refresh_token(db, jti, str(user["_id"])))

    logger.info("login_success", email=payload.email, client_ip=client_ip)

    return UserLoginResponse(
        access_token=token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user["role"],
        expire_in_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        full_name=user["full_name"],
        username=user["username"],
    )


async def refresh_token(data: UserRefreshTokenRequest, db: AsyncIOMotorDatabase) -> UserRefreshTokenResponse:
    """Refresh the user's access token using a valid refresh token."""

    try:
        # Decode the refresh token to get the payload
        payload = jwt.decode(data.refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    # Create new access and refresh tokens
    new_access_token = create_user_token(user_id=user_id, role=payload.get("role"))  # type: ignore
    new_refresh_token, new_refresh_token_jti = create_refresh_token(user_id=user_id, role=payload.get("role"))  # type: ignore

    # Revoke the old refresh token and store the new one in the database
    token_doc = await db.refresh_tokens.find_one_and_update(
        {"jti": jti, "revoked": False},
        {
            "$set": {
                "revoked": True,
                "replaced_by": new_refresh_token_jti,
                "revoked_at": datetime.now(timezone.utc),
            },
        },
    )

    # If the token was not found or already revoked, raise an error
    if token_doc is None:
        existing = await db.refresh_tokens.find_one({"jti": jti})
        if not existing:
            logger.warning("refresh_token_not_found", jti=jti, user_id=user_id)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found.")

        logger.warning("refresh_token_already_revoked", jti=jti, user_id=user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked.")

    # Check if the user exists in the database
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        logger.warning("refresh_token_user_not_found", jti=jti, user_id=user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    # Store the new refresh token in the database
    await db.refresh_tokens.insert_one(
        {
            "jti": new_refresh_token_jti,
            "user_id": user_id,
            "issued_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            "revoked": False,
            "replaced_by": None,
        }
    )

    return UserRefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expire_in_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


async def logout_user(request: UserRefreshTokenRequest, db: AsyncIOMotorDatabase) -> dict:
    """Logs out the user by invalidating their token."""

    try:
        payload = jwt.decode(request.refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")

    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.") from e

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    updated_doc = await db.refresh_tokens.find_one_and_update(
        {"jti": jti, "revoked": False},
        {
            "$set": {
                "revoked": True,
                "revoked_at": datetime.now(timezone.utc),
            },
        },
    )

    if updated_doc is None:
        existing = await db.refresh_tokens.find_one({"jti": jti})
        if not existing:
            logger.warning("logout_token_not_found", jti=jti, user_id=user_id)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found.")

        logger.warning("logout_token_already_revoked", jti=jti, user_id=user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has already been revoked.")

    logger.info("logout_success", jti=jti, user_id=user_id)

    return {"message": "Successfully logged out."}

import asyncio
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import HTTPException, Request, status
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext

from src.config.logging import get_logger
from src.config.settings import settings
from src.core.auth import create_user_token
from src.core.email import generate_token, hash_token, send_verification_email
from src.db_schemas.users import UserLoginRequest, UserLoginResponse, UserRegisterRequest, UserRegisterResponse

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
dummy_hash = pwd_context.hash("dummy-password-for-timing-attack-prevention")


def hash_password(password: str) -> str:
    """hash a plain text using bcrypt."""

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""

    return pwd_context.verify(plain_password, hashed_password)


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
        "is_active": True,
        "is_email_verified": False,
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

    token = create_user_token(str(user["_id"]))

    logger.info("login_success", email=payload.email, client_ip=client_ip)

    return UserLoginResponse(
        access_token=token,
        token_type="bearer",
        expire_in_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        full_name=user["full_name"],
        username=user["username"],
    )


async def logout_user(request: Request, db: AsyncIOMotorDatabase):
    """Logs out the user by invalidating their token."""

    # Extract the token from the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header.")

    token = auth_header.split(" ")[1]

    # Here you would implement token invalidation logic, such as storing the token in a blacklist.
    # For demonstration purposes, we'll just log the logout action.

    logger.info("logout_success", token=token, client_ip=request.client.host if request.client else "unknown")

    return {"message": "Logged out successfully."}

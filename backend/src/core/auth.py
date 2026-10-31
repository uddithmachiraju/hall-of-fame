from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Callable, Literal
from uuid import uuid4

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt  # type: ignore
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.config.logging import get_logger
from src.config.settings import settings
from src.db.mongo_db import get_db

bearer_scheme = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


def create_user_token(user_id: str, role: str) -> str:
    """Generate a JWT token for the given user id."""

    jti = str(uuid4())
    user_sub = str(user_id)
    now = datetime.now(timezone.utc)
    issued_at = int(now.timestamp())
    expires_at = int((now + timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS)).timestamp())

    return jwt.encode(
        {
            "jti": jti,
            "sub": user_sub,
            "iat": issued_at,
            "exp": expires_at,
            "role": role,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_user_token(token: str) -> Any:
    """Decode a JWT token and return the user_id if valid"""

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.error("token_decoding_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials.")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Extract and validate the user ID from the JWT token in the request header."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing token.")

    payload = decode_user_token(credentials.credentials)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authnetication credentials.")

    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    logger.info("user_authenticated", user_id=str(user["_id"]))
    return user


def require_role(*allowed_roles: Literal["admin", "user"]) -> Callable:
    """Dependency to require a specific role for an endpoint."""

    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:

        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You don't have the permission to access this resource."
            )
        return current_user

    return role_checker

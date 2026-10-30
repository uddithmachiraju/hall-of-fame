from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt  # type: ignore

from src.config.settings import settings


def create_user_token(user_id: str) -> str:
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
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

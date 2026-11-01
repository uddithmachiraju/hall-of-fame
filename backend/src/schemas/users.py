from pydantic import BaseModel, Field


class UserLoginRequest(BaseModel):
    """Request model for user login."""

    email: str = Field(..., description="Email of the user")
    password: str = Field(..., description="Password of the user")


class UserLoginResponse(BaseModel):
    """Response model for user login."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Type of the token")
    role: str = Field(..., description="Role of the user")
    expire_in_minutes: int = Field(..., description="Token expiration time in minutes")
    full_name: str = Field(..., description="Full name of the user")
    username: str = Field(..., description="Username of the user")


class UserRegisterRequest(BaseModel):
    """Request model for user registration."""

    full_name: str = Field(..., description="Full name of the user")
    username: str = Field(..., description="Username of the user")
    email: str = Field(..., description="Email of the user")
    password: str = Field(..., description="Password of the user")
    region_code: str | None = Field(None, description="Region code of the user")


class UserRegisterResponse(BaseModel):
    """Response model for user registration."""

    id: str = Field(..., description="Unique identifier of the user")
    username: str = Field(..., description="Username of the user")
    email: str = Field(..., description="Email of the user")
    is_active: bool = Field(..., description="Indicates if the user is active")
    is_email_verified: bool = Field(..., description="Indicates if the user's email is verified")
    created_at: str = Field(..., description="Timestamp when the user was created")


class UserRefreshTokenRequest(BaseModel):
    """Request model for refreshing JWT token."""

    refresh_token: str = Field(..., description="JWT refresh token")


class UserRefreshTokenResponse(BaseModel):
    """Response model for refreshing JWT token."""

    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    expire_in_minutes: int = Field(..., description="Token expiration time in minutes")

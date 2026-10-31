from datetime import datetime

from pydantic import BaseModel, Field


class GameCreateRequest(BaseModel):
    """Request schema for creating a new game."""

    slug: str = Field(..., description="Unique URL-friendly identifier for the game.")
    name: str = Field(..., description="Name of the sport or game.")


class Game(BaseModel):
    """Response schema for a single game."""

    id: str = Field(..., description="inserted ID for the created game.")
    slug: str = Field(..., description="Unique identifier of the game.")
    name: str = Field(..., description="Name of the sport or game.")
    is_active: bool = Field(..., description="Indicates whether the game is active.")
    created_at: datetime = Field(..., description="Timestamp when the game was created.")
    updated_at: datetime = Field(..., description="Timestamp when the game was updated.")


class GameResponse(BaseModel):
    """Response schema for a list of games."""

    games: list[Game] = Field(..., description="List of available games.")
    total: int = Field(..., description="Total number of games.")

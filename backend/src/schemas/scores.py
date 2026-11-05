from pydantic import BaseModel, Field
from uuid import UUID
from src.schemas.leaderboards import BoardStanding

class SubmitScoreRequest(BaseModel):
    """Schema for submitting a new score."""

    game_id: str = Field(default=..., description="Slug of the game the points were earned in")
    points: int = Field(default=..., description="Points to add")
    event_id: UUID = Field(default=..., description="Client generated id, reused only when the same win is retried")


class SubmitScoreResponse(BaseModel):
    """Schema for the response after submitting a score."""

    event_id: UUID = Field(default=..., description="The event ID associated with the score submission")
    duplicate: bool = Field(default=..., description="Indicates if the score submission was a duplicate")
    standings: list[BoardStanding] = Field(default=..., description="List of the player's standings across relevant leaderboards")

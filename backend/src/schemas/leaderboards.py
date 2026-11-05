from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class BoardSpecification:
    """A specification for creating a leaderboard."""

    key: str = field(default_factory=str, metadata={"description": "The key of the leaderboard in Redis."})
    scope: str = field(default_factory=str, metadata={"description": "The scope of the leaderboard (e.g., global, friends, etc.)."})
    period_type: str = field(default_factory=str, metadata={"description": "The time period for the leaderboard (e.g., daily, weekly, monthly)."})
    bucket: str = field(default_factory=str, metadata={"description": "Tie-break bucket for this event on this board."})
    expire_at: int = field(default_factory=int, metadata={"description": "The expiration time for the leaderboard entry in seconds."})


@dataclass(frozen=True, slots=True)
class BoardStanding:

    board_key: str = field(default_factory=str, metadata={"description": "The key of the leaderboard in Redis."})
    rank: int | None = field(default_factory=lambda: None, metadata={"description": "The rank of theplayer on the leaderboard."})
    scope: str = field(default_factory=str, metadata={"description": "The scope of the leaderboard (e.g., global, friends, etc.)."})
    score: int | None = field(default_factory=lambda: None, metadata={"description": "The score of the player on the leaderboard."})
    period_type: str = field(default_factory=str, metadata={"description": "The time period for the leaderboard (e.g., daily, weekly, monthly)."})

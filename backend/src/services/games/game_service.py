from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from src.config.logging import get_logger
from src.schemas.games import Game, GameCreateRequest, GameResponse

logger = get_logger(__name__)


async def create_game(payload: GameCreateRequest, db: AsyncIOMotorDatabase) -> Game:
    """Creates a game and return the persisted document of game."""

    now = datetime.now(timezone.utc)

    game_document: dict[str, str | bool | datetime] = {
        "slug": payload.slug,
        "name": payload.name,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = await db.games.insert_one(game_document)
    except DuplicateKeyError as exc:
        logger.info("game_creation_rejected", slug=payload.slug, details="duplicate slug found")
        raise ValueError("A game with this slug already exists.") from exc

    game_document["_id"] = result.inserted_id
    logger.info("game_created", slug=payload.slug, id=result.inserted_id)

    return Game(
        id=str(game_document["_id"]),
        slug=payload.slug,
        name=payload.name,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


async def get_games(db: AsyncIOMotorDatabase) -> GameResponse:
    """Retrieve all active games."""

    cursor = db.games.find(
        {"is_active": True},
        {
            "slug": 1,
            "name": 1,
            "is_active": 1,
            "created_at": 1,
            "updated_at": 1,
        },
    ).sort("name", 1)

    games: list[Game] = []

    async for document in cursor:
        games.append(
            Game(
                id=str(document["_id"]),
                slug=document["slug"],
                name=document["name"],
                is_active=document["is_active"],
                created_at=document["created_at"],
                updated_at=document["updated_at"],
            )
        )

    return GameResponse(
        games=games,
        total=len(games),
    )

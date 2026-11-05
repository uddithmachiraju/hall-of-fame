from src.schemas.leaderboards import BoardSpecification, BoardStanding
from src.config.settings import settings
from src.config.logging import get_logger
from src.schemas.scores import SubmitScoreRequest, SubmitScoreResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis, RedisError
from bson import ObjectId
import json
from datetime import datetime, timezone
from typing import Callable, Awaitable
from pymongo.errors import PyMongoError
from src.services.leaderboard.leaderboard_service import build_leaderboard_specs, BUCKET_BITS, SCORE_SHIFT, MAX_SCORE, MAX_BUCKET

logger = get_logger(__name__)


async def _cached(redis: Redis, key: str, ttl: int, loader: Callable[[], Awaitable[dict | None]]) -> dict | None:
    """Read-through JSON cache. Cache failures degrade to a DB read, never to an error."""

    try:
        raw = await redis.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception as e:
        logger.error("redis_error", error=str(e))

    # If not found in cache, load the value using the loader function.
    value = await loader()
    try:
        await redis.set(key, json.dumps(value), ex=ttl if value is not None else 30)
    except Exception as e:
        logger.error("redis_error", error=str(e))
    return value

async def _get_player_standings(redis: Redis, boards: list[BoardSpecification], player_id: str) -> list[BoardStanding]:
    """Fetches the player's standings for the given leaderboard specifications."""

    async with redis.pipeline(transaction=False) as pipe:
        for board in boards:
            pipe.zscore(board.key, player_id)
            pipe.zrank(board.key, player_id)
        results = await pipe.execute()

    out = []
    for i, board in enumerate(boards):
        composite, rank = results[2 * i], results[2 * i + 1]
        out.append(
            BoardStanding(
                board_key=board.key,
                score=int(composite) if composite is not None else 0,
                scope=board.scope,
                rank=int(rank) + 1 if rank is not None else None,
                period_type=board.period_type
            )
        )
    return out

async def submit_score(player_id: str, score_request: SubmitScoreRequest, db: AsyncIOMotorDatabase, redis: Redis):
    """Submits a new score for a player."""

    # Ensure game and player are active and valid.
    try:
        # Check if the game exists and is active
        game = await _cached(
            redis, f"game:{score_request.game_id}", settings.REDIS_CACHE_TTL,
            lambda: db.games.find_one(
                {
                    "slug": score_request.game_id,
                    "active": True
                },
            ),
        )
        if not game:
            logger.error("game_not_found", game_id=score_request.game_id)
            raise ValueError("Game not found")

        if not game["is_active"]:
            logger.error("game_inactive", game_id=score_request.game_id)
            raise ValueError("Game is inactive")

        # Check if the player exists and is active
        player = await _cached(
            redis, f"player:{player_id}", settings.REDIS_CACHE_TTL,
            lambda: db.players.find_one(
                {
                    "_id": ObjectId(player_id),
                    "active": True
                },
            ),
        )

    except PyMongoError as exc:
        logger.error("score_db_error", game_id=score_request.game_id, player_id=player_id, error=str(exc))
        raise ValueError("Temporarily unavailable.") from exc

    if not player:
        logger.error("player_not_found", player_id=player_id)
        raise ValueError("Player not found or inactive.")

    if not player["is_active"]:
        logger.error("player_inactive", player_id=player_id)
        raise ValueError("Player is inactive.")

    # Build leaderboard specifications based on the current time and player's region.
    now = datetime.now(timezone.utc)
    region = player.get("region_code") or "global"
    boards = build_leaderboard_specs(game_slug=score_request.game_id, now=now, region_code=region)

    # Generate the leaderboard keys to be updated, including the event-specific leaderboard and the general event leaderboard.
    keys = [f"lb:idem:{score_request.event_id}", "lb.events", *(b.key for b in boards)]
    args: list = [
        7 * 24 * 3600, score_request.points, player_id, SCORE_SHIFT, MAX_SCORE, MAX_BUCKET,
        score_request.event_id, score_request.game_id, now.isoformat(), json.dumps([b.key for b in boards]),
    ]

    for b in boards:
        args += [b.bucket, b.expire_at]

    try:
        script = redis.register_script(
            open("src/lua_scripts/register_leaderboard_event.lua").read()
        )

        reply = await script(keys=keys, args=args)

        if int(reply[0]) == 0:
            standings = await _get_player_standings(redis, boards, player_id)
            logger.info("score_duplicate", player_id=player_id, game_id=score_request.game_id, event_id=score_request.event_id)
            return {"message": "Duplicate score submission. No changes made.", "standings": standings}

    except RedisError as exc:
        logger.error("score_redis_error", game_id=score_request.game_id, player_id=player_id, error=str(exc))
        raise ValueError("Temporarily unavailable.") from exc

    standings = [
        BoardStanding(b.key, int(reply[1 + 2 * i]), b.scope, int(reply[2 + 2 * i]), b.period_type)
        for i, b in enumerate(boards)
    ]
    logger.info("score_submitted", player_id=player_id, game_id=score_request.game_id, event_id=score_request.event_id, standings=[s.__dict__ for s in standings])
    return SubmitScoreResponse(
        event_id=score_request.event_id,
        duplicate=False,
        standings=standings
    )

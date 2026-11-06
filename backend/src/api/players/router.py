from fastapi import APIRouter, status, Depends
from src.schemas.scores import SubmitScoreRequest, SubmitScoreResponse
from src.db.mongo_db import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.core.auth import require_role
from src.services.player.player_service import submit_score
from redis.asyncio import Redis
from src.core.redis import get_redis_client


router = APIRouter()

@router.post("/scores", response_model=SubmitScoreResponse, status_code=status.HTTP_202_ACCEPTED)
async def add_score(score_request: SubmitScoreRequest, db: AsyncIOMotorDatabase = Depends(get_db), redis: Redis = Depends(get_redis_client), player: dict = Depends(require_role("admin", "user"))):
    """Submits a score for the player."""

    return await submit_score(str(player["_id"]), score_request, db, redis)

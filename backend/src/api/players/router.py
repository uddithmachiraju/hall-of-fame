from fastapi import APIRouter, status, Depends
from src.schemas.scores import SubmitScoreRequest, SubmitScoreResponse
from src.db.mongo_db import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.core.auth import require_role
from src.services.player.player_service import submit_score
from redis.asyncio import Redis
from src.core.redis import get_redis_client


router = APIRouter()

@router.post("/{player_id}/scores", response_model=SubmitScoreResponse, status_code=status.HTTP_202_ACCEPTED)
async def add_score(player_id: str, score_request: SubmitScoreRequest, db: AsyncIOMotorDatabase = Depends(get_db), redis: Redis = Depends(get_redis_client), auth: dict = Depends(require_role("admin", "user"))):
    """Submits a score for the player."""

    return await submit_score(player_id, score_request, db, redis)

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.auth import require_role
from src.db.mongo_db import get_db
from src.schemas.games import Game, GameCreateRequest, GameResponse
from src.services.games import game_service

router = APIRouter()


@router.post("/create", response_model=Game, status_code=status.HTTP_201_CREATED)
async def post_game(
    payload: GameCreateRequest, db: AsyncIOMotorDatabase = Depends(get_db), admin: dict = Depends(require_role("admin"))
) -> Game:
    """Create a new game. Admin access required"""

    response = await game_service.create_game(payload=payload, db=db)
    return response


@router.get("/", response_model=GameResponse, status_code=status.HTTP_200_OK)
async def get_games(
    db: AsyncIOMotorDatabase = Depends(get_db), auth: dict = Depends(require_role("admin", "user"))
) -> GameResponse:
    """Get all the games in the database."""

    response = await game_service.get_games(db=db)
    return response

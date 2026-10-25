from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.db.mongo_db import get_db
from src.db_schemas.users import UserLoginRequest, UserLoginResponse

router = APIRouter()


@router.post("/login", response_model=UserLoginResponse)
async def login(payload: UserLoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """User login endpoint."""
    pass

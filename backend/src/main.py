import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth.router import router as auth_router
from src.config.logging import get_logger, setup_logging
from src.config.settings import get_settings
from src.db.mongo_db import check_db_health

settings = get_settings()
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("app_starting", env=settings.ENV, version=settings.APP_VERSION)

    if not await check_db_health():
        logger.error(
            "database_connection_failed", database=settings.MONGO_URI, env=settings.ENV, version=settings.APP_VERSION
        )
        raise RuntimeError("Database connection failed. Application startup aborted.")

    yield

    logger.info("app_stopping", env=settings.ENV, version=settings.APP_VERSION)


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan, debug=settings.DEBUG)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware to add process time header to the response."""

    start_time = time.monotonic()
    response = await call_next(request)
    process_time = (round(time.monotonic() - start_time) * 1000, 2)
    response.headers["X-Process-Time"] = str(process_time)
    return response


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENV == "development",
        workers=1,
    )

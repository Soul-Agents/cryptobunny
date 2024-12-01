from contextlib import asynccontextmanager
from typing import AsyncGenerator
from db import TweetDB


@asynccontextmanager
async def get_db() -> AsyncGenerator[TweetDB, None]:
    db = TweetDB()
    try:
        yield db
    finally:
        await db.close()

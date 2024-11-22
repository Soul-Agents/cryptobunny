from contextlib import contextmanager
from typing import Generator
from db import TweetDB


@contextmanager
def get_db() -> Generator[TweetDB, None, None]:
    db = TweetDB()
    try:
        yield db
    finally:
        db.close()

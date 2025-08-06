"""Configuration for the athlete service."""

import os
import asyncio

from typing import Annotated

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from fastapi import Depends
from app.models import Base

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

# Use asyncpg driver for async operations
DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
CONNECT_ARGS = {"echo": False, "future": True}

engine = create_async_engine(DB_URL, **CONNECT_ARGS)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False)


async def create_db_and_tables():
    """Try to connect to DB with retries."""
    retries = 5
    for i in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all, checkfirst=True)
            print("✅ DB connection successful.")
            break
        except Exception as e:
            print(f"❌ DB connection failed (attempt {i + 1}/{retries}): {e}")
            await asyncio.sleep(3)
    else:
        raise RuntimeError("Could not connect to the database after retries")


async def get_session():
    """Get an async session for the database."""
    async with async_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

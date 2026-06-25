from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

async_engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession]:
	async with async_session() as session:
		yield session

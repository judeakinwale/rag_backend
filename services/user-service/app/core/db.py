from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=True,  # Set to True for SQL query logging, False in production
    pool_pre_ping=True,  # Enable connection pool pre-ping to avoid stale connections
)

async_session = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db():
    async with async_session() as session:
        yield session

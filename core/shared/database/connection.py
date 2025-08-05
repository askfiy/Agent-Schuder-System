from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config import env_helper


engine = create_async_engine(
    env_helper.ASYNC_DB_URL,
    # echo=True,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,  # 明确指定使用 AsyncSession
)

__all__ = ["engine", "AsyncSessionLocal"]

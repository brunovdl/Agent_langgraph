import os
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./session.db")

@asynccontextmanager
async def get_checkpointer():
    """Abre o checkpointer certo para DATABASE_URL (Postgres ou SQLite), já com as tabelas criadas."""
    if DATABASE_URL.startswith("sqlite"):
        caminho = DATABASE_URL.split("///"[1])
        async with AsyncSqliteSaver.from_conn_string(caminho) as checkpointer:
            await checkpointer.setup()
            yield checkpointer
    else:
        conn_string = DATABASE_URL.replace("postgressql+asyncpg://", "postgresql://")
        async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
            await checkpointer.setup()
            yield checkpointer
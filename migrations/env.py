import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import pool
from webhook_service import models
from alembic import context
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from webhook_service.database import Base
from webhook_service.config import Config

target_metadata = Base.metadata
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Get URL from your Config object instead of alembic.ini
    url = Config.SQLALCHEMY_DATABASE_URI

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(Config.SQLALCHEMY_DATABASE_URI)


    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

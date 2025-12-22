import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# optional: load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

config = context.config

# prefer env var over ini
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# import your project's Base.metadata
# adjust this import if your Base lives elsewhere
try:
    from app.models.base import Base  # common path: backend/app/models/base.py
except Exception as e:
    raise RuntimeError("Update alembic/env.py to import your SQLAlchemy Base") from e

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

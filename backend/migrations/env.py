from alembic import context
from sqlalchemy import engine_from_config, pool
from backend.app.database import Base, DATABASE_URL
from backend.app import models

config = context.config
config.set_main_option('sqlalchemy.url', DATABASE_URL.replace('%', '%%'))

if context.is_offline_mode():
    context.configure(url=DATABASE_URL, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix='sqlalchemy.', poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

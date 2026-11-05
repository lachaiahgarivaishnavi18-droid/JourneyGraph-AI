import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .deployment import database_url


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


IS_VERCEL = os.getenv('VERCEL') == '1'
if IS_VERCEL:
    os.environ.setdefault('APP_ENV', 'production')
    os.environ.setdefault('CHECKPOINT_DB', '/tmp/journeygraph-checkpoints.db')
DATABASE_URL = database_url(os.environ)
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')

SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as session:
        yield session

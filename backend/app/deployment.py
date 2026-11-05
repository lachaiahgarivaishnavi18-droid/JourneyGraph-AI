"""Serverless deployment configuration and serialized PostgreSQL bootstrap."""
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import text


def database_url(environ):
    raw = environ.get('DATABASE_URL', 'sqlite:///./journeygraph.db')
    if environ.get('VERCEL') == '1' and not raw.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
        raise RuntimeError('Vercel requires DATABASE_URL for managed PostgreSQL; local SQLite files cannot provide shared durable storage')
    if raw.startswith('postgres://'):
        raw = 'postgresql+psycopg://' + raw[len('postgres://'):]
    elif raw.startswith('postgresql://'):
        raw = 'postgresql+psycopg://' + raw[len('postgresql://'):]
    return raw


@contextmanager
def serverless_bootstrap(engine, enabled):
    """One cold-start instance migrates/seeds at a time; no secret values logged."""
    if not enabled:
        yield None
        return
    if engine.dialect.name != 'postgresql':
        raise RuntimeError('Managed PostgreSQL is required for Vercel deployment')
    # Transaction-scoped locks also work with pooled PostgreSQL URLs. Keep
    # migrations and seeding on this same connection until the outer commit.
    with engine.begin() as connection:
        connection.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': 752196104})
        from alembic.config import Config
        from alembic import command
        backend = Path(__file__).resolve().parents[1]
        config = Config(str(backend / 'alembic.ini'))
        config.set_main_option('script_location', str(backend / 'migrations'))
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
        yield connection

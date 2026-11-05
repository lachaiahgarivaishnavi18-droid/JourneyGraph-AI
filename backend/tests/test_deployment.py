from pathlib import Path
import json
import tomllib
import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic import command
from backend.app.deployment import database_url
from backend.app.models import Customer


@pytest.mark.parametrize('prefix', ['postgres://', 'postgresql://', 'postgresql+psycopg://'])
def test_provider_postgresql_urls_select_installed_driver(prefix):
    result = database_url({'VERCEL': '1', 'DATABASE_URL': prefix + 'user:password@db.example.test/app?sslmode=require'})
    assert result == 'postgresql+psycopg://user:password@db.example.test/app?sslmode=require'


@pytest.mark.parametrize('configuration', [{}, {'DATABASE_URL': 'sqlite:////tmp/app.db'}])
def test_vercel_cannot_silently_use_an_instance_local_database(configuration):
    with pytest.raises(RuntimeError, match='managed PostgreSQL'):
        database_url({'VERCEL': '1', **configuration})


def test_local_sqlite_configuration_remains_available():
    assert database_url({}) == 'sqlite:///./journeygraph.db'


def test_migration_and_seed_session_share_supplied_transaction(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'deployment.db'))
    with engine.connect() as connection:
        outer = connection.begin()
        config = Config('backend/alembic.ini')
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
        assert 'graph_relationships' in inspect(connection).get_table_names()
        with Session(bind=connection) as db:
            db.add(Customer(id='TRANSACTION-TEST', name='Synthetic transaction test'))
            db.commit()
        assert outer.is_active  # Session commits must not release the bootstrap lock.
        outer.rollback()
    with engine.connect() as connection:
        assert connection.scalar(select(Customer.id).where(Customer.id == 'TRANSACTION-TEST')) is None
    engine.dispose()


def test_vercel_build_routes_to_real_backend_and_keeps_frontend_assets():
    config = json.loads(Path('vercel.json').read_text())
    project = tomllib.loads(Path('pyproject.toml').read_text())
    assert project['tool']['vercel']['entrypoint'] == 'backend.app.main:app'
    assert 'frontend/dist/**' in config['functions']['backend/app/main.py']['includeFiles']
    assert project['tool']['vercel']['fastapi']['static']['cdn'] is True

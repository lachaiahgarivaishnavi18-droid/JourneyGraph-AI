import os
import json
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

os.environ['SEED_DEMO'] = 'false'
os.environ['APP_ENV'] = 'test'
os.environ['ADMIN_PASSWORD'] = 'testing-password-only'
from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models import User, Customer, CustomerEvent, GraphRelationship
from backend.app.security import hash_password, attempts
from backend.app.analytics import analytics, segment_customers
from backend.app.data import seed_demo


@pytest.fixture
def client(tmp_path):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    def session():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = session
    os.environ['CHECKPOINT_DB'] = str(tmp_path / 'checkpoints.db')
    attempts.clear()
    with factory() as db:
        db.add(User(id='admin', email='admin@example.test', password_hash=hash_password('test-password-123'), role='admin'))
        db.commit()
    with TestClient(app) as c:
        c.factory = factory
        login = c.post('/api/auth/login', json={'email': 'admin@example.test', 'password': 'test-password-123'})
        assert login.status_code == 200
        c.headers['Authorization'] = 'Bearer ' + login.json()['access_token']
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def customer(client, id_='C001'):
    response = client.post('/api/customers', json={'id': id_, 'name': 'Test Customer'})
    assert response.status_code == 201


def event(client, id_, type_, time, **kwargs):
    return client.post('/api/events', json={'event_id': id_, 'customer_id': 'C001', 'event_type': type_, 'entity_id': 'P001', 'channel': 'website', 'event_time': time, **kwargs})


def test_auth_and_roles(client):
    assert client.get('/api/auth/me').json()['role'] == 'admin'
    assert client.post('/api/auth/login', json={'email': 'admin@example.test', 'password': 'wrong-password'}).status_code == 401
    r = client.post('/api/auth/register', json={'email': 'viewer@example.test', 'password': 'viewer-password-123'})
    assert r.status_code == 201
    login = client.post('/api/auth/login', json={'email': 'viewer@example.test', 'password': 'viewer-password-123'}).json()
    assert client.post('/api/customers', json={'id': 'X', 'name': 'X'}, headers={'Authorization': 'Bearer ' + login['access_token']}).status_code == 403
    assert client.get('/api/customers', headers={'Authorization': 'Bearer bad'}).status_code == 401


def test_customers_ingestion_and_ordered_journey(client):
    customer(client)
    assert event(client, 'E2', 'purchase', '2026-01-02T12:00:00Z', properties={'amount': 100}).status_code == 201
    assert event(client, 'E1', 'product_view', '2026-01-01T12:00:00Z').status_code == 201
    assert event(client, 'E1', 'product_view', '2026-01-01T12:00:00Z').status_code == 409
    assert event(client, 'BAD', 'purchase', '2026-01-02', properties={'amount': -1}).status_code == 422
    assert client.get('/api/customers').json()['total'] == 1
    journey = client.get('/api/journeys/C001').json()
    assert [e['id'] for e in journey['events']] == ['E1', 'E2']
    assert client.get('/api/customers/C001').json()['monetary'] == 100


def test_temporal_graph_both_clocks_and_expiry(client):
    customer(client)
    event(client, 'E1', 'product_view', '2026-01-01T10:00:00Z', valid_to='2026-01-03T10:00:00Z')
    assert not client.get('/api/graph/explore', params={'at': '2025-12-31T00:00:00Z'}).json()['edges']
    assert len(client.get('/api/graph/explore', params={'at': '2026-01-02T00:00:00Z'}).json()['edges']) == 2
    assert not client.get('/api/graph/explore', params={'at': '2026-01-04T00:00:00Z'}).json()['edges']
    assert not client.get('/api/graph/explore', params={'known_at': '2026-01-02T00:00:00Z'}).json()['edges']
    compare = client.get('/api/graph/history', params={'before': '2025-12-31T00:00:00Z', 'after': '2026-01-02T00:00:00Z'}).json()
    assert len(compare['added']) == 2
    assert client.post('/api/graph/build').json()['relationships'] == 2
    assert client.post('/api/graph/build').json()['relationships'] == 2


def test_analytics_denominators_and_funnel(client):
    customer(client)
    customer(client, 'C002')
    for i, type_ in enumerate(['website_visit', 'product_view', 'add_to_cart', 'purchase']):
        event(client, f'E{i}', type_, f'2026-01-0{i+1}T10:00:00Z', properties={'amount': 80} if type_ == 'purchase' else {})
    result = client.get('/api/analytics/overview').json()
    assert result['metrics']['conversion_rate'] == 50
    assert result['metrics']['observed_value_per_customer'] == 40
    assert [f['customers'] for f in result['funnel']] == [1, 1, 1, 1]
    filtered = client.get('/api/analytics/overview?channel=website').json()
    assert filtered['metrics']['conversion_rate'] == 100
    assert client.get('/api/analytics/overview?start=bad').status_code == 422


def test_import_preview_atomic_validation_duplicates(client):
    content = 'id,name\nC001,One\nC001,Duplicate\nC002,Two\n'
    preview = client.post('/api/imports/preview', data={'kind': 'customers'}, files={'file': ('customers.csv', content, 'text/csv')}).json()
    assert preview['valid'] == 2 and preview['duplicates'] == 1
    imported = client.post('/api/imports', data={'kind': 'customers'}, files={'file': ('customers.csv', content, 'text/csv')}).json()
    assert imported['inserted'] == 2
    data = [{'event_id': 'GOOD', 'customer_id': 'C001', 'event_type': 'search', 'entity_id': 'P', 'channel': 'website', 'event_time': '2026-01-01T00:00:00Z'}, {'event_id': 'BAD'}]
    rejected = client.post('/api/imports', files={'file': ('events.json', json.dumps(data))}).json()
    assert rejected['status'] == 'rejected'
    assert client.get('/api/events').json()['total'] == 0
    data.pop()
    result = client.post('/api/imports', files={'file': ('events.json', json.dumps(data))}).json()
    assert result['inserted'] == 1
    assert len(client.get('/api/graph/explore').json()['edges']) == 2


def test_llm_recommendations_workflow_and_report(client, monkeypatch):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    customer(client)
    event(client, 'E1', 'add_to_cart', '2026-01-01T00:00:00Z')
    result = client.post('/api/llm/query', json={'question': 'Why do customers abandon carts?'}).json()
    assert result['mode'] == 'local-evidence-summary'
    assert result['evidence_ids'] == ['analytics:funnel']
    recommendation = client.post('/api/recommendations/generate', json={'customer_id': 'C001'}).json()[0]
    assert recommendation['status'] == 'pending_human_review'
    assert recommendation['evidence_ids'] == ['E1']
    run = client.post('/api/agents/run', json={'customer_id': 'C001', 'include_predictions': False}).json()
    assert run['status'] == 'completed', run
    assert 'prediction' not in run['outputs']
    assert len(client.get('/api/agents/executions/' + run['id']).json()['steps']) == 8
    assert client.post('/api/predictions/churn', json={}).json()['status'] == 'insufficient_data'
    report = client.post('/api/reports/generate', json={}).json()
    export = client.get('/api/reports/' + report['id'] + '/export?format=csv')
    assert export.status_code == 200 and 'total_customers,1' in export.text
    for kind in ('customers', 'journeys'):
        scoped = client.post('/api/reports/generate', json={'kind': kind}).json()
        assert len(scoped['data']['records']) == 1
        assert 'C001' in client.get('/api/reports/' + scoped['id'] + '/export?format=csv').text


def test_mapped_import_and_unknown_references(client):
    content = 'person,label\nMAPPED,Mapping Test\n'
    imported = client.post('/api/imports', data={'kind': 'customers', 'mapping': '{"person":"id","label":"name"}'}, files={'file': ('mapped.csv', content)}).json()
    assert imported['inserted'] == 1
    assert client.get('/api/customers/MAPPED').status_code == 200
    response = event(client, 'UNKNOWN', 'search', '2026-01-01T00:00:00Z')
    assert response.status_code == 422
    assert client.get('/api/graph/explore').json()['edges'] == []
    assert client.get('/api/graph/history', params={'before': '2026-02-01T00:00:00Z', 'after': '2026-01-01T00:00:00Z'}).status_code == 422


def test_external_llm_invalid_evidence_falls_back(client, monkeypatch):
    import backend.app.intelligence as intelligence
    monkeypatch.setenv('LLM_API_KEY', 'test-only-key-not-a-real-secret')
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'choices': [{'message': {'content': json.dumps({'narrative': 'Invented 99999 customers', 'evidence_ids': ['analytics:overview'], 'limitations': []})}}]}
    monkeypatch.setattr(intelligence.httpx, 'post', lambda *args, **kwargs: Response())
    result = client.post('/api/llm/query', json={'question': 'Summarize this dataset'}).json()
    assert result['mode'] == 'local-evidence-summary'
    assert 'provider_error' in result
    assert '99999' not in result['narrative']


def test_synthetic_model_evaluation_and_complete_workflow(client):
    with client.factory() as db:
        seed_demo(db)
        segment_customers(db)
        db.commit()
    for kind in ['churn', 'conversion']:
        result = client.post('/api/predictions/' + kind, json={'customer_id': 'C001'}).json()
        assert result['status'] == 'evaluated', result
        assert 0 <= result['metrics']['roc_auc'] <= 1
        assert result['metrics']['train_labels_until'] == result['metrics']['holdout_features_until']
        assert len(result['scores']) == 1
    run = client.post('/api/agents/run', json={'customer_id': 'C001'}).json()
    assert run['status'] == 'completed', run
    assert len(run['outputs']) == 9

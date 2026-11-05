import os
import csv
import io
import json
import secrets
from pathlib import Path
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError, BaseModel, Field
from .database import Base, engine, get_db, SessionLocal, now
from .models import User, Customer, CustomerEvent, Product, Execution, AgentOutput, ImportRecord, AuditLog, Report, Setting, Recommendation
from .schemas import Credentials, CustomerInput, EventInput, RunInput, QueryInput, utc
from .security import current_user, editor, admin, hash_password, verify_password, token, rate_limit, audit
from .data import seed_demo, add_event
from .analytics import analytics, profile, journey, events_query, event_dict, segment_customers
from .temporal_graph import LocalGraphStore, Neo4jGraphStore
from .intelligence import run_workflow, recommend, answer, AGENTS
from .ml import predict


def serialize(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@asynccontextmanager
async def lifespan(app):
    if os.getenv('APP_ENV') == 'test':
        yield
        return
    if os.getenv('APP_ENV') != 'production':
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        email = os.getenv('ADMIN_EMAIL', 'admin@journeygraph.local')
        if not db.scalar(select(User).where(User.email == email)):
            password = os.getenv('ADMIN_PASSWORD')
            if not password and os.getenv('APP_ENV') == 'production':
                raise RuntimeError('Set ADMIN_PASSWORD before first production startup')
            if not password:
                password = secrets.token_urlsafe(18)
                print(f'\nLocal administrator: {email}\nGenerated password: {password}\nSet ADMIN_PASSWORD to use a persistent chosen password.\n', flush=True)
            if len(password) < 10:
                raise RuntimeError('ADMIN_PASSWORD must be at least 10 characters')
            db.add(User(id=str(uuid4()), email=email, password_hash=hash_password(password), role='admin'))
            db.commit()
        if os.getenv('SEED_DEMO', 'true').lower() == 'true':
            seed_demo(db)
            segment_customers(db)
            db.commit()
    yield


app = FastAPI(title='JourneyGraph AI', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','), allow_credentials=False, allow_methods=['GET', 'POST', 'PUT'], allow_headers=['Authorization', 'Content-Type'])


@app.middleware('http')
async def headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content={'detail': 'Record conflicts with an existing record or reference'})


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '1.0.0'}


@app.post('/api/auth/register', status_code=201)
def register(payload: Credentials, request: Request, db=Depends(get_db)):
    rate_limit(request)
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, 'Email already registered')
    user = User(id=str(uuid4()), email=payload.email, password_hash=hash_password(payload.password), role='viewer')
    db.add(user)
    audit(db, user, 'register')
    db.commit()
    return {'id': user.id, 'email': user.email, 'role': user.role}


@app.post('/api/auth/login')
def login(payload: Credentials, request: Request, db=Depends(get_db)):
    rate_limit(request)
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, 'Invalid email or password')
    audit(db, user, 'login')
    db.commit()
    return {'access_token': token(user), 'token_type': 'bearer', 'user': {'id': user.id, 'email': user.email, 'role': user.role}}


@app.get('/api/auth/me')
def me(user=Depends(current_user)):
    return {'id': user.id, 'email': user.email, 'role': user.role}


class RoleInput(BaseModel):
    role: str = Field(pattern='^(viewer|analyst|admin)$')


@app.get('/api/users')
def users(user=Depends(admin), db=Depends(get_db)):
    return [{'id': u.id, 'email': u.email, 'role': u.role} for u in db.scalars(select(User))]


@app.put('/api/users/{id_}/role')
def change_role(id_: str, payload: RoleInput, user=Depends(admin), db=Depends(get_db)):
    target = db.get(User, id_)
    if not target:
        raise HTTPException(404, 'User not found')
    if target.id == user.id:
        raise HTTPException(409, 'Cannot change your own administrator role')
    target.role = payload.role
    audit(db, user, 'role_changed', {'user_id': id_, 'role': payload.role})
    db.commit()
    return {'id': id_, 'role': target.role}


def filters(start: str | None = None, end: str | None = None, channel: str | None = None, product: str | None = None, event_type: str | None = None, segment: str | None = None, stage: str | None = None):
    try:
        result = dict(start=utc(start) if start else None, end=utc(end) if end else None, channel=channel, product=product, event_type=event_type, segment=segment, stage=stage)
    except ValueError:
        raise HTTPException(422, 'Dates must be ISO timestamps including timezone')
    if result['start'] and result['end'] and result['start'] > result['end']:
        raise HTTPException(422, 'start must not be after end')
    return result


@app.get('/api/customers')
def customers(search: str = '', segment: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user=Depends(current_user), db=Depends(get_db)):
    query = select(Customer).order_by(Customer.id)
    if search:
        query = query.where(Customer.name.ilike(f'%{search[:100]}%') | Customer.id.ilike(f'%{search[:100]}%'))
    rows = [profile(db, c.id) for c in db.scalars(query)]
    if segment:
        rows = [r for r in rows if r['segment'] == segment]
    return {'items': rows[(page-1)*page_size:page*page_size], 'total': len(rows), 'page': page, 'page_size': page_size}


@app.get('/api/customers/{id_}')
def customer(id_: str, user=Depends(current_user), db=Depends(get_db)):
    result = profile(db, id_)
    if not result:
        raise HTTPException(404, 'Customer not found')
    return result


@app.post('/api/customers', status_code=201)
def create_customer(payload: CustomerInput, user=Depends(editor), db=Depends(get_db)):
    if db.get(Customer, payload.id):
        raise HTTPException(409, 'Customer ID already exists')
    db.add(Customer(**payload.model_dump(), source='manual'))
    audit(db, user, 'customer_created', {'customer_id': payload.id})
    db.commit()
    return profile(db, payload.id)


@app.put('/api/customers/{id_}')
def update_customer(id_: str, payload: CustomerInput, user=Depends(editor), db=Depends(get_db)):
    row = db.get(Customer, id_)
    if not row:
        raise HTTPException(404, 'Customer not found')
    if id_ != payload.id:
        raise HTTPException(422, 'Customer ID is immutable')
    for k, v in payload.model_dump(exclude={'id'}).items():
        setattr(row, k, v)
    row.updated_at = now()
    audit(db, user, 'customer_updated', {'customer_id': id_})
    db.commit()
    return profile(db, id_)


@app.get('/api/products')
def products(user=Depends(current_user), db=Depends(get_db)):
    return [serialize(p) for p in db.scalars(select(Product))]


@app.get('/api/events')
def events(f=Depends(filters), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), user=Depends(current_user), db=Depends(get_db)):
    rows = events_query(db, **f)
    return {'items': [event_dict(e) for e in rows[(page-1)*page_size:page*page_size]], 'total': len(rows), 'page': page}


@app.post('/api/events', status_code=201)
def ingest(payload: EventInput, user=Depends(editor), db=Depends(get_db)):
    try:
        event = add_event(db, payload, 'api')
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not event:
        raise HTTPException(409, 'Event ID already exists')
    audit(db, user, 'event_ingested', {'event_id': payload.event_id})
    db.commit()
    return event_dict(event)


@app.get('/api/customers/{id_}/events')
def customer_events(id_: str, user=Depends(current_user), db=Depends(get_db)):
    if not db.get(Customer, id_):
        raise HTTPException(404, 'Customer not found')
    return [event_dict(e) for e in events_query(db, customer_id=id_)]


@app.get('/api/journeys')
def journeys(user=Depends(current_user), db=Depends(get_db)):
    return [{'customer_id': c.id, 'name': c.name, **{k: v for k, v in journey(db, c.id).items() if k != 'events'}} for c in db.scalars(select(Customer))]


@app.get('/api/journeys/{id_}')
def get_journey(id_: str, f=Depends(filters), user=Depends(current_user), db=Depends(get_db)):
    if not db.get(Customer, id_):
        raise HTTPException(404, 'Customer not found')
    return journey(db, id_, **f)


@app.get('/api/analytics/overview')
def overview(f=Depends(filters), user=Depends(current_user), db=Depends(get_db)):
    return analytics(db, **f)


@app.get('/api/analytics/{kind}')
def analysis(kind: str, f=Depends(filters), user=Depends(current_user), db=Depends(get_db)):
    result = analytics(db, **f)
    keys = {'funnel': 'funnel', 'conversion': 'trend', 'dropoffs': 'funnel', 'channels': 'channels', 'cohorts': 'cohorts', 'segments': 'segments', 'patterns': 'paths'}
    if kind not in keys:
        raise HTTPException(404, 'Unknown analytics operation')
    return {'items': result[keys[kind]], 'metrics': result['metrics'], 'definitions': result['definitions']}


@app.post('/api/segments/refresh')
def refresh_segments(user=Depends(editor), db=Depends(get_db)):
    result = segment_customers(db)
    audit(db, user, 'segments_refreshed')
    db.commit()
    return result


@app.post('/api/graph/build')
def build_graph(user=Depends(editor), db=Depends(get_db)):
    result = LocalGraphStore(db).build()
    audit(db, user, 'graph_built', result)
    db.commit()
    return result


@app.get('/api/graph/explore')
def explore(at: str | None = None, known_at: str | None = None, customer_id: str | None = None, user=Depends(current_user), db=Depends(get_db)):
    try:
        return LocalGraphStore(db).snapshot(at, known_at, customer_id)
    except ValueError:
        raise HTTPException(422, 'Invalid timestamp')


@app.get('/api/graph/customer/{id_}')
def customer_graph(id_: str, at: str | None = None, known_at: str | None = None, user=Depends(current_user), db=Depends(get_db)):
    return explore(at, known_at, id_, user, db)


@app.get('/api/graph/history')
def history(before: str, after: str, known_at: str | None = None, user=Depends(current_user), db=Depends(get_db)):
    try:
        if utc(before) > utc(after):
            raise ValueError()
        return LocalGraphStore(db).compare(before, after, known_at)
    except ValueError:
        raise HTTPException(422, 'Invalid timestamps or reversed range')


@app.get('/api/graph/patterns')
def patterns(user=Depends(current_user), db=Depends(get_db)):
    return LocalGraphStore(db).patterns()


@app.post('/api/graph/neo4j/sync')
def sync_graph(user=Depends(admin), db=Depends(get_db)):
    if not os.getenv('NEO4J_URI'):
        raise HTTPException(409, 'Neo4j is not configured; SQL temporal graph is available')
    try:
        result = Neo4jGraphStore(db).sync()
    except Exception:
        raise HTTPException(502, 'Neo4j synchronization failed; SQL data is retained')
    audit(db, user, 'neo4j_synced', result)
    db.commit()
    return result


@app.get('/api/agents')
def agents(user=Depends(current_user), db=Depends(get_db)):
    latest = db.scalar(select(Execution).order_by(Execution.started_at.desc()).limit(1))
    return {'agents': [{'id': id_, 'name': name, 'description': desc, 'status': ('completed' if id_ in latest.outputs else 'not_run') if latest and latest.status == 'completed' else 'ready'} for id_, name, desc in AGENTS], 'latest_execution': serialize(latest) if latest else None}


@app.post('/api/agents/run')
def run(payload: RunInput, request: Request, user=Depends(editor), db=Depends(get_db)):
    rate_limit(request, 'workflow', 5)
    if payload.customer_id and not db.get(Customer, payload.customer_id):
        raise HTTPException(404, 'Customer not found')
    config = db.get(Setting, 'agents')
    result = run_workflow(db, customer_id=payload.customer_id, include_predictions=payload.include_predictions and (config.value.get('include_predictions', True) if config else True))
    audit(db, user, 'agents_run', {'execution_id': result.id, 'status': result.status})
    db.commit()
    return serialize(result)


@app.get('/api/agents/executions')
def executions(user=Depends(current_user), db=Depends(get_db)):
    return [serialize(x) for x in db.scalars(select(Execution).order_by(Execution.started_at.desc()).limit(100))]


@app.get('/api/agents/executions/{id_}')
def execution(id_: str, user=Depends(current_user), db=Depends(get_db)):
    row = db.get(Execution, id_)
    if not row:
        raise HTTPException(404, 'Execution not found')
    return {**serialize(row), 'steps': [serialize(x) for x in db.scalars(select(AgentOutput).where(AgentOutput.execution_id == id_).order_by(AgentOutput.created_at))]}


@app.post('/api/predictions/{kind}')
def prediction(kind: str, payload: RunInput, user=Depends(editor), db=Depends(get_db)):
    if kind not in ('churn', 'conversion'):
        raise HTTPException(404, 'Unknown prediction kind')
    if payload.customer_id and not db.get(Customer, payload.customer_id):
        raise HTTPException(404, 'Customer not found')
    result = predict(db, kind, payload.customer_id)
    audit(db, user, 'prediction_generated', {'kind': kind, 'status': result['status']})
    db.commit()
    return result


@app.get('/api/predictions/{kind}')
def stored_predictions(kind: str, user=Depends(current_user), db=Depends(get_db)):
    from .models import Prediction
    from collections import Counter
    if kind not in ('churn', 'conversion'):
        raise HTTPException(404, 'Unknown prediction kind')
    latest = {}
    for row in db.scalars(select(Prediction).where(Prediction.kind == kind).order_by(Prediction.created_at.desc())):
        latest.setdefault(row.customer_id, {**row.result, 'scored_at': row.created_at})
    counts = Counter(r['risk'] for r in latest.values())
    return {'scores': list(latest.values()), 'evaluated_customers': len(latest), 'distribution': [{'name': label, 'customers': counts[label]} for label in ('Low', 'Medium', 'High') if counts[label]], 'scope': 'Most recent persisted score per customer; independent of overview filters', 'target': '30-day inactivity proxy' if kind == 'churn' else '30-day purchase propensity'}


@app.get('/api/recommendations/{id_}')
def recommendations(id_: str, user=Depends(current_user), db=Depends(get_db)):
    return [serialize(x) for x in db.scalars(select(Recommendation).where(Recommendation.customer_id == id_).order_by(Recommendation.created_at.desc()).limit(10))]


@app.post('/api/recommendations/generate')
def generate_recommendations(payload: RunInput, user=Depends(editor), db=Depends(get_db)):
    ids = [payload.customer_id] if payload.customer_id else list(db.scalars(select(Customer.id)))
    if payload.customer_id and not db.get(Customer, payload.customer_id):
        raise HTTPException(404, 'Customer not found')
    result = [r for id_ in ids for r in recommend(db, id_)]
    audit(db, user, 'recommendations_generated', {'count': len(result)})
    db.commit()
    return result


@app.post('/api/llm/query')
def llm(payload: QueryInput, request: Request, user=Depends(current_user), db=Depends(get_db)):
    rate_limit(request, 'llm', 20)
    return answer(db, **payload.model_dump())


async def parse_import(file, kind, mapping):
    if kind not in ('customers', 'events'):
        raise HTTPException(422, 'Import kind must be customers or events')
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, 'Maximum file size is 5 MB')
    try:
        text = raw.decode('utf-8-sig')
        extension = Path(file.filename or '').suffix.lower()
        rows = json.loads(text) if extension == '.json' else list(csv.DictReader(io.StringIO(text))) if extension == '.csv' else None
        if not isinstance(rows, list) or not rows or len(rows) > 10000:
            raise ValueError('Expected 1–10,000 CSV/JSON rows')
        mapping = json.loads(mapping)
        if not isinstance(mapping, dict):
            raise ValueError('Column mapping must be an object: source column → target field')
        mapped = [{mapping.get(k, k): v for k, v in row.items()} for row in rows]
        for row in mapped:
            if kind == 'events':
                if 'id' in row and 'event_id' not in row:
                    row['event_id'] = row.pop('id')
                if isinstance(row.get('properties'), str):
                    row['properties'] = json.loads(row['properties']) if row['properties'].strip() else {}
                if row.get('valid_to') == '':
                    row['valid_to'] = None
        return mapped
    except (ValueError, UnicodeError, TypeError, AttributeError) as exc:
        raise HTTPException(422, f'Invalid upload: {str(exc)[:200]}')


def validate_rows(db, rows, kind):
    model = CustomerInput if kind == 'customers' else EventInput
    table = Customer if kind == 'customers' else CustomerEvent
    seen, valid, errors, duplicates = set(), [], [], 0
    for i, row in enumerate(rows, 2):
        try:
            parsed = model.model_validate(row)
            key = parsed.id if kind == 'customers' else parsed.event_id
            if key in seen or db.get(table, key):
                duplicates += 1
                continue
            if kind == 'events' and not db.get(Customer, parsed.customer_id):
                raise ValueError(f'Unknown customer {parsed.customer_id}')
            seen.add(key)
            valid.append(parsed)
        except (ValidationError, ValueError) as exc:
            errors.append({'row': i, 'message': str(exc).split('\n')[0][:250]})
    return valid, errors, duplicates


@app.post('/api/imports/preview')
async def preview_import(file: UploadFile = File(...), kind: str = Form('events'), mapping: str = Form('{}'), synthetic: bool = Form(False), user=Depends(editor), db=Depends(get_db)):
    rows = await parse_import(file, kind, mapping)
    valid, errors, duplicates = validate_rows(db, rows, kind)
    return {'rows': len(rows), 'valid': len(valid), 'duplicates': duplicates, 'errors': errors[:100], 'preview': [v.model_dump() for v in valid[:10]], 'columns': list(rows[0]), 'policy': 'Atomic import: invalid rows reject entire file. Duplicate IDs are skipped. Missing optional values use documented defaults.'}


@app.post('/api/imports')
async def import_data(file: UploadFile = File(...), kind: str = Form('events'), mapping: str = Form('{}'), synthetic: bool = Form(False), user=Depends(editor), db=Depends(get_db)):
    rows = await parse_import(file, kind, mapping)
    valid, errors, duplicates = validate_rows(db, rows, kind)
    result = {'rows': len(rows), 'inserted': 0, 'duplicates': duplicates, 'errors': errors[:100], 'status': 'rejected' if errors else 'completed'}
    if not errors:
        for parsed in valid:
            if kind == 'customers':
                db.add(Customer(**parsed.model_dump(), source='synthetic-demo' if synthetic else 'file-import'))
            else:
                add_event(db, parsed, 'synthetic-demo' if synthetic else 'file-import')
        db.flush()
        result['inserted'] = len(valid)
        segment_customers(db)
    db.add(ImportRecord(id=str(uuid4()), filename=Path(file.filename or 'upload').name[:255], result=result))
    audit(db, user, 'data_import', {'kind': kind, 'status': result['status'], 'inserted': result['inserted']})
    db.commit()
    return result


@app.get('/api/imports')
def imports(user=Depends(editor), db=Depends(get_db)):
    return [serialize(x) for x in db.scalars(select(ImportRecord).order_by(ImportRecord.created_at.desc()).limit(100))]


@app.get('/api/reports')
def reports(user=Depends(current_user), db=Depends(get_db)):
    return [{'id': r.id, 'title': r.title, 'created_at': r.created_at} for r in db.scalars(select(Report).order_by(Report.created_at.desc()))]


class ReportInput(BaseModel):
    title: str = Field(default='Journey intelligence report', min_length=1, max_length=160)
    kind: str = Field(default='analytics', pattern='^(analytics|customers|journeys)$')


@app.post('/api/reports/generate')
def generate_report(payload: ReportInput, f=Depends(filters), user=Depends(editor), db=Depends(get_db)):
    data = {**analytics(db, **f), 'report_kind': payload.kind}
    if payload.kind == 'customers':
        ids = sorted({e.customer_id for e in events_query(db, **f)}) if any(f.values()) else list(db.scalars(select(Customer.id)))
        data['records'] = [profile(db, id_) for id_ in ids]
    elif payload.kind == 'journeys':
        ids = sorted({e.customer_id for e in events_query(db, **f)})
        data['records'] = [journey(db, id_, **f) for id_ in ids]
    row = Report(id=str(uuid4()), title=payload.title, data=data)
    db.add(row)
    audit(db, user, 'report_generated', {'report_id': row.id})
    db.commit()
    return serialize(row)


def csv_safe(value):
    text = str(value)
    return "'" + text if text.startswith(('=', '+', '-', '@', '\t', '\r')) else text


@app.get('/api/reports/{id_}/export')
def export_report(id_: str, format: str = 'json', user=Depends(current_user), db=Depends(get_db)):
    row = db.get(Report, id_)
    if not row:
        raise HTTPException(404, 'Report not found')
    if format == 'json':
        data, mime = json.dumps(serialize(row), indent=2), 'application/json'
    elif format == 'csv':
        stream = io.StringIO()
        writer = csv.writer(stream)
        if row.data.get('report_kind') in ('customers', 'journeys') and row.data.get('records'):
            records = row.data['records']
            writer.writerow(records[0].keys())
            writer.writerows([csv_safe(json.dumps(v) if isinstance(v, (list, dict)) else v) for v in r.values()] for r in records)
        else:
            writer.writerow(['metric', 'value'])
            writer.writerows([csv_safe(k), csv_safe(v)] for k, v in row.data['metrics'].items())
        data, mime = stream.getvalue(), 'text/csv'
    else:
        raise HTTPException(422, 'format must be json or csv')
    return StreamingResponse(iter([data]), media_type=mime, headers={'Content-Disposition': f'attachment; filename="journeygraph-{id_}.{format}"'})


@app.get('/api/settings')
def settings(user=Depends(current_user), db=Depends(get_db)):
    return {'llm': {'configured': bool(os.getenv('LLM_API_KEY')), 'model': os.getenv('LLM_MODEL', 'gpt-4.1-mini'), 'mode': 'external-llm' if os.getenv('LLM_API_KEY') else 'local-evidence-summary'}, 'graph': {'storage': 'SQL temporal tables + NetworkX', 'neo4j_configured': bool(os.getenv('NEO4J_URI'))}, 'settings': {s.key: s.value for s in db.scalars(select(Setting))}, 'data_sources': dict(__import__('collections').Counter(e.source for e in events_query(db)))}


class SettingsInput(BaseModel):
    enabled: bool = True
    include_predictions: bool = True


@app.put('/api/settings/{key}')
def save_settings(key: str, payload: SettingsInput, user=Depends(admin), db=Depends(get_db)):
    if key not in ('llm', 'agents'):
        raise HTTPException(422, 'Unknown configuration key')
    db.merge(Setting(key=key, value=payload.model_dump()))
    audit(db, user, 'settings_updated', {'key': key})
    db.commit()
    return payload


@app.get('/api/audit')
def audit_logs(user=Depends(admin), db=Depends(get_db)):
    return [serialize(x) for x in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))]


frontend = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if frontend.is_dir():
    app.mount('/', StaticFiles(directory=str(frontend), html=True), name='frontend')

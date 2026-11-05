# JourneyGraph-AI

An academic customer journey intelligence application with a React dashboard,
FastAPI API, SQL-backed temporal knowledge graph, nine-agent LangGraph workflow,
and evaluated inactivity/conversion models. Runs locally without an LLM key.

## Start on this Windows workspace

Python 3.12 and Node 22+ are recommended. Dependencies and a Python 3.12 virtual
environment have already been installed in this checkout.

```powershell
.\scripts\start.ps1
```

Open **http://127.0.0.1:8000**. The first startup prints a generated administrator
password for `admin@journeygraph.local`. Copy that password from the terminal.
To choose a password before the **first** startup of a new database:

```powershell
$env:ADMIN_PASSWORD = 'choose-a-long-unique-password'
.\scripts\start.ps1
```

Changing ADMIN_PASSWORD does not change an existing account. Local JWT signing
keys are generated per process unless JWT_SECRET is configured, so restarting
the server requires signing in again. The browser keeps its bearer token in
session storage and clears it on an authentication failure.

For a fresh checkout, create a Python 3.12 virtual environment and install/build:

```powershell
python -m venv .venv
.\scripts\start.ps1 -Install
```

Install [pnpm](https://pnpm.io/installation) first if it is not available. If your
system Python is 3.15, select a Python 3.12 executable when creating `.venv`;
some scientific dependencies do not support development Python releases.

## Development

Run from the repository root in terminal one:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

In terminal two:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to FastAPI. For one-server mode,
run `pnpm build` in frontend and restart FastAPI. The API serves `frontend/dist`
when it exists. Hash routing supports direct page links without server rewrites.

Interactive API documentation: http://127.0.0.1:8000/docs. Login using the JSON
`/api/auth/login` operation, then paste the returned bearer token into Authorize.

## Demonstration walkthrough

1. **Dashboard** shows calculated counts, ordered funnel, daily activity, RFM
   segments, and channel conversion. Synthetic provenance is prominently labeled.
2. **Data Import** accepts customers/events CSV or JSON. Select kind, optionally
   map source columns to target fields, validate, inspect errors/duplicates, then
   import. Mark the synthetic-data checkbox when using sample files. The entire file is rejected if any row is invalid. Duplicate IDs are
   skipped. Customers must exist before their events are imported.
3. **Customer Directory** searches customers; selecting a row opens their profile
   and ordered event timeline. **Journey Explorer** accepts a customer ID.
4. **Knowledge Graph Explorer** shows actual stored facts. Click nodes or edges
   for details. Set valid-at and known-at timestamps independently; timestamps
   entered in the browser are converted from local time to UTC.
5. **Historical Graph Comparison** compares two global snapshots. The before
   value must precede the valid-at value. **Graph Pattern Discovery** counts
   consecutive transitions by distinct customer.
6. **AI Agent Dashboard** runs all agents or one customer's workflow. Unchecking
   predictions exercises the conditional branch. Inspect persisted outputs and
   execution history. Agents are actual computations, not animations.
7. **Churn Risk Analysis** / **Conversion Prediction** train a logistic model and
   evaluate a later 30-day outcome window. Small or single-class datasets return
   an insufficient-data result. All scores disclose model limitations.
8. **Next Best Action** creates evidence-linked proposals for human review. No
   message, discount, or customer intervention is sent by this application.
9. **Natural Language Analytics** retrieves allowlisted analytics evidence and
   provides a labeled deterministic summary without a key. Optional LLM narration
   uses the retrieved evidence and rejects unknown citations/numeric claims.
10. **Reports** freezes calculated analytics, customer profiles, or full journeys
    and exports JSON/CSV. **Audit Logs**
    records mutations and execution IDs. **System Settings** manages user roles;
    new self-registrations are viewers, and only administrators can change roles.

All 48 requested navigation entries are present. Related views share reusable
components and analysis services. Global date/channel/segment/product/event/stage
filters apply to overview and journey analytics; other tools expose their own
customer/time scope. Each page identifies its scope.

## Data and definitions

The initial synthetic dataset contains 120 customers and 180 days of linked
interactions. `data/samples` contains customer/event CSV and JSON plus products,
orders, campaigns, channels, and support CSVs. `scripts/seed.py` regenerates them
on an empty database. The application seeds only when no customers exist.
Set `SEED_DEMO=false` before starting a clean database to import only your data.

- Conversion = distinct purchasing customers / selected customer population.
- Unfiltered population = registered customers; filtered population = customers
  with matching events. Definitions are returned in every overview response.
- Active = event in 30 days relative to the latest matching recorded event.
- Retention and inactivity are activity proxies, not verified contractual churn.
- Observed value is recorded purchases less returns divided by population. The
  Customer Lifetime Value page explicitly labels recorded value, not a forecast.
- Channel conversion is descriptive and does not establish marketing attribution.
- Funnel stages must occur sequentially within selected events.
- Segmentation uses documented RFM rules, not an undisclosed clustering model.

## Configuration

`.env.example` lists configuration. Docker Compose reads `.env`; local Python
reads process environment variables (it does not automatically load `.env`).

| Variable | Purpose |
| --- | --- |
| DATABASE_URL | SQLAlchemy SQLite or `postgresql+psycopg://…` connection |
| ADMIN_EMAIL / ADMIN_PASSWORD | Bootstrap administrator on a new database |
| JWT_SECRET | Stable signing secret; ≥32 characters required in production |
| SEED_DEMO | `true` seeds an empty database; use `false` for your own data |
| LLM_API_KEY | Optional provider key, server only |
| LLM_BASE_URL / LLM_MODEL | OpenAI-compatible chat-completions endpoint/model |
| CHECKPOINT_DB | SQLite LangGraph checkpoint file |
| NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD | Optional graph projection service |
| CORS_ORIGINS | Comma-separated permitted browser origins |

Without a key, analytics and all deterministic agents still work. External LLM
and Neo4j connections are optional and never reported as successful unless the
service call succeeds. Provider prompts omit customer names and email addresses.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
pnpm test
pnpm build
```

The optional Playwright critical workflow expects running backend and synthetic
data. It starts the Vite frontend unless one is already serving:

```powershell
$env:E2E_PASSWORD = 'your-local-admin-password'
pnpm exec playwright install chromium
pnpm test:e2e
```

To test the one-server build with an existing Chrome installation, also set
`E2E_BASE_URL=http://127.0.0.1:8000` and `E2E_BROWSER_CHANNEL=chrome`. The browser
tests create labeled synthetic records and save desktop/mobile dashboard images
under `docs/`.

See [validation evidence](docs/VALIDATION.md) for executed checks and limits.

## Docker

For a shareable presentation deployment, the repository includes a Render
Blueprint. See [Render deployment instructions](docs/RENDER_DEPLOYMENT.md) for
generated credentials, deployment checks, and the free plan's storage limits.

```powershell
Copy-Item .env.example .env
# Set ADMIN_PASSWORD and a long JWT_SECRET in .env.
docker compose up --build
```

Open http://127.0.0.1:8000. SQLite and workflow checkpoints persist in a named
volume. To use PostgreSQL, set POSTGRES_PASSWORD and DATABASE_URL to
`postgresql+psycopg://journeygraph:YOUR_PASSWORD@postgres:5432/journeygraph`, then:

```powershell
docker compose --profile postgres up -d postgres --wait
docker compose up --build app
```

For Neo4j set a strong NEO4J_PASSWORD, NEO4J_URI=`bolt://neo4j:7687`, start
`docker compose --profile neo4j up -d neo4j`, then call the administrator-only
`POST /api/graph/neo4j/sync`. SQL is the authoritative temporal store; the default
explorer uses SQL. The Neo4j adapter also supports parameterized snapshots.

Production deployment requires APP_ENV=production, SEED_DEMO=false, a persistent
JWT_SECRET, strong administrator credentials, database backups, HTTPS at a reverse
proxy, and environment-specific infrastructure review. Run Alembic migrations
before startup (the Docker entrypoint does this). This is a demonstrable academic
implementation, not a claim of audited production readiness. Docker/PostgreSQL/
Neo4j/provider integrations require verification in their target environment.

See [architecture](docs/ARCHITECTURE.md), [API guide](docs/API.md), and
[implementation plan](docs/IMPLEMENTATION_PLAN.md).

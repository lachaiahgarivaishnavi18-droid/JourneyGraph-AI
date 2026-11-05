# API guide

The generated OpenAPI document at `/openapi.json` and interactive `/docs` are the
canonical request schemas. All `/api` operations except health/register/login
require `Authorization: Bearer <token>`.

| Group | Operations |
| --- | --- |
| Authentication | POST /auth/register, POST /auth/login, GET /auth/me |
| Users | GET /users, PUT /users/{id}/role (administrator) |
| Customers | GET/POST /customers, GET/PUT /customers/{id}, GET /customers/{id}/events |
| Catalog | GET /products |
| Events | GET/POST /events |
| Journeys | GET /journeys, GET /journeys/{id} |
| Analytics | GET /analytics/overview, /funnel, /conversion, /dropoffs, /channels, /cohorts, /segments, /patterns |
| Segments | POST /segments/refresh |
| Graph | POST /graph/build, GET /graph/explore, /graph/customer/{id}, /graph/history, /graph/patterns |
| Neo4j | POST /graph/neo4j/sync (administrator, optional) |
| Agents | GET /agents, POST /agents/run, GET /agents/executions, GET /agents/executions/{id} |
| Predictions | POST /predictions/churn, POST /predictions/conversion |
| Recommendations | GET /recommendations/{id}, POST /recommendations/generate |
| Natural language | POST /llm/query |
| Imports | POST /imports/preview, POST /imports, GET /imports |
| Reports | GET /reports, POST /reports/generate, GET /reports/{id}/export?format=json or csv |
| Administration | GET /settings, PUT /settings/llm, PUT /settings/agents, GET /audit |

All paths above have the `/api` prefix. Mutations require analyst/admin unless
explicitly administrator-only. Reports are immutable snapshots. Import history
requires analyst/admin; audit and user role management require administrator.

Customer listing: search, segment, page (1-based), page_size (≤100). Events:
page_size ≤200 and shared analytics filters. Shared filters: start/end ISO UTC
timestamps, channel, product, event_type, segment, stage. Populations and metric
definitions are returned in overview responses. Unknown timestamps and reversed
date ranges return 422.

Graph exploration: at (valid time), known_at (transaction time), customer_id.
Graph history: before, after, optional known_at. Both snapshots are global.

Event example:

```json
{"event_id":"MY-E001","customer_id":"MY-C001","event_type":"purchase","entity_id":"P001","channel":"website","event_time":"2026-11-01T10:00:00Z","properties":{"amount":149}}
```

Recorded time is assigned by the server. Never trust an uploaded recorded_at.
Event IDs are immutable/idempotent: duplicate API IDs return 409; duplicate
import IDs are skipped and counted.

Imports use multipart fields file, kind (`customers` or `events`) and mapping
(JSON source-column → canonical-field map). JSON files must be arrays. CSV event
properties may be a quoted JSON object. Invalid rows reject the entire file and
the response gives row numbers and error summaries. Optional customer email
defaults to empty and region to Unknown; event properties default to `{}`.

Agent/prediction/recommendation body: `{"customer_id":"C001"}` or `{}` for
population scope; workflow also supports `include_predictions:false`. Queries:
`{"question":"Which channels convert?","customer_id":null}`.

Errors: 401 unauthenticated, 403 role denied, 404 missing resource, 409 duplicate
or configuration conflict, 413 large upload, 422 validation, 429 local rate limit,
502 optional Neo4j connectivity. Login/register share a 15/minute IP limit; LLM
20/minute and workflow 5/minute. These limits are process-local for local use.

Design references: [FastAPI JWT security](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
and [LangGraph checkpoint compilation](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/compile).

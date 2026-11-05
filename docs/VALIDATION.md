# Executed validation

Date: 5 November 2026 (Asia/Calcutta). This was an empty repository at the start.

## Automated checks

| Check | Observed result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest -q --tb=short` | **9 passed**, final backend run 102.07 s |
| `pnpm test` in frontend | **5 passed** across two files, final run 6.34 s |
| `pnpm build` in frontend | TypeScript and Vite passed; largest chunk 413.80 kB; no chunk-size warning |
| Playwright (`pnpm test:e2e`) against local backend using installed Chrome | **2 passed**, 19.9 s |
| Alembic upgrade on fresh migration-check SQLite database | Passed |
| Alembic check against migrated schema | No new upgrade operations detected |
| Python compileall for backend and seed script | Passed |
| Compose YAML parser | Parsed app, PostgreSQL and Neo4j service definitions |
| Responsive browser check and screenshots | Desktop 1440×1000 and mobile 390×844 passed; dedicated first-workflow rerun **1 passed**, 11.3 s |

Backend coverage includes login, invalid credentials, viewer write denial,
customer listing/creation, event validation/deduplication, ordered journey
reconstruction, graph build idempotence, valid and transaction clock filtering,
valid-to expiry, graph comparison, metric denominators, sequential funnels,
CSV preview/import, atomic JSON rejection, mapped columns, unknown references,
LangGraph conditional routing and all-agent execution, local LLM fallback,
rejection of unsupported provider numbers (mock provider), insufficient ML data,
forward-window evaluated churn/conversion, evidence-linked recommendations, and
analytics/customer/journey report exports.

Frontend unit tests cover auth headers, expired session handling, 48 unique page
routes, table pagination, keyboard selection, and error/empty states.

Playwright verifies real browser login, calculated dashboard cards, customer
profile navigation, graph rendering and an empty historical snapshot. A second
test imports a unique synthetic customer CSV and linked JSON events, checks the
resulting timeline, retrieves a labeled local answer, generates a report, and
downloads its JSON. Tests use only local synthetic records.

Desktop and mobile captures are saved as dashboard-desktop.jpg and
dashboard-mobile.jpg next to this document. The screenshot contains the original
120 demo customers plus the synthetic upload verification records.

## Interactive verification

The in-app browser independently confirmed:

- Admin sign-in and synthetic provenance banner.
- Customer search and chronological profile timeline.
- Persisted temporal graph and zero relationships before the data begins.
- Successful nine-agent customer run with all nine completion states and actual
  structured profile, analytics, model and recommendation output.
- Upload preview/import of import-demo-customers.csv and import-demo-events.json.
  Four events appeared in order with channel changes and the correct purchase.
- Natural-language channel question answered with calculated numerator and
  denominator, local-fallback label, citations and attribution limitations.
- Analytics report generation with JSON and CSV download controls.

## Corrections made during verification

- Pytest temporary files now stay inside the workspace (Windows sandbox access).
- Test application startup no longer creates a real local bootstrap account.
- Frontend build permission/configuration issues and one JSX syntax error fixed.
- Graph time controls use explicit form submission; the pre-dataset snapshot was
  retested successfully in both in-app browser and Playwright.
- Charts render without initial animation, so screenshots show completed data.
- Tables support keyboard selection, and chart/graph bundles are separated.
- Reports distinguish analytics, customer profiles, and full journey exports.
- Sample uploads can explicitly retain a synthetic provenance label.

## Verification limits

Docker is not installed here: the Dockerfile/Compose configuration has not been
built or run. PostgreSQL, Neo4j and external LLM credentials were not provided,
so those integrations are implemented/configurable but were not exercised live.
The invalid-response provider guard was tested with a mock; this does not verify
a real provider. SQLite is the database exercised by the automated suite.

The prediction metrics are computed on synthetic data; they do not establish
real customer performance. Activity/inactivity labels and observed customer value
have the limitations documented in ARCHITECTURE.md. No production load test,
penetration test, multi-tenant isolation, or independent security audit is claimed.

Preview databases and generated test artifacts are ignored by Git. Normal startup
uses its own database and generates a fresh bootstrap password on first launch.

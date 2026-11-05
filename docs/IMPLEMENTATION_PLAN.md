# JourneyGraph AI implementation plan

Repository inspection: 5 November 2026. The repository contains only Git metadata;
there are no existing sources, dependencies, tests, or application components.

The requested deliverable is a local academic full-stack application with Docker
deployment, so implementation stays in this checkout. A hosted static Site cannot
run the requested Python backend.

## Phases

1. Foundation: FastAPI, SQLAlchemy, migrations, authentication, role checks, audit.
2. Data: deterministic synthetic dataset, atomic CSV/JSON imports, validation.
3. Analytics: shared filtered event queries, customer profiles, funnels, cohorts.
4. Temporal graph: persisted event edges, valid/transaction-time snapshots,
   comparison, NetworkX traversal, optional Neo4j synchronization.
5. Intelligence: typed LangGraph workflow, persisted executions and checkpoints,
   RFM segments, evaluated temporal holdout prediction, grounded recommendations.
6. LLM: allowlisted analytics retrieval, deterministic local answers, optional
   OpenAI-compatible structured responses.
7. Interface: responsive React/TypeScript dashboard, customer and graph explorers,
   timeline, agent runs, imports, reports, administration, themes.
8. Verification and delivery: backend integration tests, frontend tests/build,
   critical browser workflows when runtime support is available, Docker and docs.

## Invariants

- Every displayed metric comes from stored data and identifies its population.
- Synthetic data and non-LLM fallback outputs are explicitly labeled.
- Imported events retain provenance and UTC event and recorded times.
- Graph snapshots independently filter valid time and transaction time.
- Predictions report a temporal holdout and never equate synthetic performance
  with production validity. Insufficient labels yield no model score.
- Recommendations never send messages or perform customer interventions.
- Secrets remain server-side. New registrations receive viewer privileges.

## Verification

Run focused backend tests after backend/data/graph/intelligence changes, then the
complete suite. Run frontend unit tests and TypeScript/Vite build after interface
work. Record actual commands/results and known limitations in docs/VALIDATION.md.

## Delivery status

All eight implementation phases above are implemented for local demonstration.
The end-to-end workflow is verified with API integration tests, frontend tests,
and real Playwright browser tests. Deployment assets and optional PostgreSQL,
Neo4j, and LLM adapters are included; live external-service/container verification
remains environment-dependent. See VALIDATION.md for exact executed evidence.

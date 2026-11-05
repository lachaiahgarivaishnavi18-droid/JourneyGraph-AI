# Vercel frontend and backend deployment

The repository root is configured as one Vercel FastAPI project. The build command
builds the existing React application into frontend/dist. FastAPI mounts that
directory, and Vercel promotes the static assets to its CDN. The existing /api
routes run as a Python function under the same domain. No frontend API hostname
or CORS rewrite is needed for this arrangement.

## Required account and database setup

1. Install and connect the Vercel integration in Codex, or sign in to your Vercel
   dashboard and import the JourneyGraph-AI GitHub repository.
2. Keep the project Root Directory at the repository root, not frontend/ or
   backend/. Use the FastAPI preset and the committed vercel.json configuration.
3. Connect managed PostgreSQL through the Vercel Marketplace (for example Neon),
   using an available free plan if appropriate. Do not provision paid resources
   without approving their cost. Use a separate database for preview deployments
   so preview builds cannot mutate the presentation database.
4. Set the runtime environment variables below in Vercel before deploying. Store
   secret values only in Vercel; never commit them to GitHub or paste them into
   public documentation. Vercel account access and PostgreSQL credentials are
   required to finish a real deployment.

## Runtime environment variables

| Name | Value or source |
| --- | --- |
| DATABASE_URL | Managed PostgreSQL connection URL, with provider-required SSL options |
| APP_ENV | production |
| JWT_SECRET | Random secret of at least 32 characters; keep stable across deployments |
| ADMIN_EMAIL | admin@journeygraph.local, or a chosen administrator email |
| ADMIN_PASSWORD | Strong password of at least 10 characters; first bootstrap only |
| SEED_DEMO | true for the synthetic presentation dataset |
| VERCEL_SUPPORT_LARGE_FUNCTIONS | 1 if the Python bundle needs the large-functions beta |
| OMP_NUM_THREADS | 1 |
| OPENBLAS_NUM_THREADS | 1 |
| MKL_NUM_THREADS | 1 |
| LLM_API_KEY | Optional provider credential; omit for labeled local summaries |

VERCEL=1 is supplied by the platform. In that environment the backend rejects
SQLite as its primary database. Provider postgres:// and postgresql:// URLs are
normalized to the installed psycopg driver. Local SQLite and Docker operation
remain available outside Vercel.

## Startup and persistence

On cold start, a transaction-scoped PostgreSQL advisory lock serializes database
migrations, administrator bootstrap and demo seeding. Alembic and bootstrap share
the same database connection and transaction, including when a pooled database
URL is used. Demo events and graph facts are inserted in batches to reduce
database round trips. Existing nonempty customer data is not seeded again.

Customers, events, temporal relationships, agent outputs, predictions,
recommendations, reports and audits persist in PostgreSQL. Workflow checkpoint
files use /tmp and are instance-local: durable resume across cold starts is not
provided. Completed execution evidence is stored in PostgreSQL. A persistent
LangGraph checkpoint backend is a separate enhancement if cross-instance resume
is needed.

## Function limits and presentation checks

The Python function has a configured maximum duration of 300 seconds. Imports
are capped at 4 MiB to leave room below Vercel's 4.5 MB request limit. Synchronous
agent runs must finish within the function duration; high-volume use should move
analysis to a durable task queue. The ML libraries may require the large-functions
beta. Availability, quotas, and database terms depend on the connected accounts.

After Vercel reports the deployment as ready, verify the actual returned URL:

1. GET /api/health returns status ok.
2. The root serves the React login page and its assets load.
3. Log in with the deployed administrator credentials, not the local password.
4. Confirm the dashboard shows labeled synthetic data and computed metrics.
5. Import a small customer/events sample, inspect its journey and temporal graph,
   run agents, and export a report.
6. Confirm data remains available across separate function instances and later
   requests. Do not claim persistence based on a single successful request.

This source configuration alone does not establish that a live deployment exists.
The final domain and deployment status must come from Vercel after account and
database setup succeeds.

Official documentation:
- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/docs/functions/runtimes/python
- https://vercel.com/docs/functions/limitations

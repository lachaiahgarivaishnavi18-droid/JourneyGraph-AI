# Render presentation deployment

This configuration deploys the actual React and FastAPI application from the
GitHub main branch. It does not replace backend operations with static results.

## Configuration

The root render.yaml defines one Docker web service on the free plan, with the
health endpoint /api/health. The container first applies Alembic migrations, then
starts Uvicorn on Render's PORT. React is built into the same Docker image and
served by FastAPI. Same-origin browser requests require no separate frontend URL.

Render generates ADMIN_PASSWORD and JWT_SECRET as runtime environment variables.
No secret values are stored in GitHub. ADMIN_EMAIL is admin@journeygraph.local.
Retrieve the generated ADMIN_PASSWORD from the service's Environment settings
when signing in for the first time; the locally generated password is unrelated.
Do not share the administrator password publicly. Viewers can register their own
accounts; an administrator can grant analyst access for upload/agent testing.

SEED_DEMO=true loads synthetic data on a clean database. The LLM key is optional;
without it, the deployed app labels its deterministic evidence summaries. Local
ML models and the SQL temporal graph remain available.

## Deploy

Connect Render to the account used for deployment and authorize this repository.
Create a new Blueprint using the repository's render.yaml, verify the free plan,
and start deployment. If using the ordinary Web Service form instead, choose
Docker and apply the environment variables from render.yaml; generate strong
ADMIN_PASSWORD and JWT_SECRET values in Render rather than adding them to Git.

Repository: https://github.com/lachaiahgarivaishnavi18-droid/JourneyGraph-AI

Wait for Render to report the deploy as live, then verify:

1. The actual returned https://...onrender.com/api/health responds with status ok.
2. The site root displays the login page.
3. Sign-in works using the deployed service's generated administrator password.
4. The dashboard labels synthetic data and shows calculated metrics.
5. A customer journey, historical graph query, agent run, and report export work.

Do not infer a live hostname from the requested service name: Render may allocate
a suffix. Share only the URL returned by the successful deployment.

## Free plan limitations

The free plan sleeps after inactivity and uses ephemeral storage. SQLite data,
uploads, user accounts, workflow history and checkpoints can be lost on restart
or redeploy. The synthetic seed is rebuilt and administrator credentials are
recreated from the configured environment variables. Export important reports
beforehand and open the site ahead of the presentation to allow a cold start.

Persistent storage requires a separate deployment decision: a paid disk or an
external PostgreSQL database and a durable workflow checkpoint strategy. This
configuration does not provision paid infrastructure or external API usage.

Official references:
- https://render.com/docs/blueprint-spec
- https://render.com/docs/docker
- https://render.com/docs/free

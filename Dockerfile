FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
RUN corepack enable && corepack prepare pnpm@11.25.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY backend/ ./backend/
COPY --from=frontend /build/frontend/dist ./frontend/dist
COPY data/ ./data/
COPY scripts/start-container.sh ./scripts/start-container.sh
RUN mkdir /app/storage && chown -R appuser:appuser /app
USER appuser
ENV PORT=8000 DATABASE_URL=sqlite:////app/storage/journeygraph.db CHECKPOINT_DB=/app/storage/checkpoints.db
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health', timeout=4)"
CMD ["sh", "/app/scripts/start-container.sh"]

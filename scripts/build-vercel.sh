#!/bin/sh
set -eu

# Build the React application into the directory mounted by FastAPI.
# Vercel promotes this static mount to its CDN and keeps /api on Python.
npx --yes pnpm@11.25.0 --dir frontend install --frozen-lockfile
npx --yes pnpm@11.25.0 --dir frontend build

"""FastAPI application entrypoint for Compliance Copilot."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ingest, query

app = FastAPI(title="Compliance Copilot API")

# The Next.js frontend calls this API from the browser, which makes every
# request cross-origin. Without this the browser rejects the preflight and no
# request reaches the app at all. Origins are an allow-list rather than "*"
# so a deployed frontend URL must be named explicitly.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(ingest.router)
app.include_router(query.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

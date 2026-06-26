"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from a2a.server.routes import add_a2a_routes_to_fastapi
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from a2a_mesh.agents.echo import build_echo_routes
from a2a_mesh.core.redis import close_redis, get_redis
from a2a_mesh.db.session import AsyncSessionLocal
from a2a_mesh.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    logger.info("A2A-Mesh starting up")
    yield
    await close_redis()
    logger.info("A2A-Mesh shut down")


app = FastAPI(
    title="A2A-Mesh",
    description="AI agent orchestration and cross-company federation platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Mount echo agent A2A routes
_card_routes, _rpc_routes = build_echo_routes()
add_a2a_routes_to_fastapi(app, agent_card_routes=_card_routes, jsonrpc_routes=_rpc_routes)


@app.get("/health")
async def health() -> JSONResponse:
    """Liveness check — verifies DB and Redis connectivity."""
    status: dict[str, str] = {"status": "ok"}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        status["db"] = "error"
        status["status"] = "degraded"

    try:
        redis = get_redis()
        await redis.ping()
        status["redis"] = "ok"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        status["redis"] = "error"
        status["status"] = "degraded"

    http_status = 200 if status["status"] == "ok" else 503
    return JSONResponse(status, status_code=http_status)

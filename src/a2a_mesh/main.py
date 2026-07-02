"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from a2a.server.routes import add_a2a_routes_to_fastapi
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text

import a2a_mesh.db.models  # noqa: F401 — registers all models with SQLAlchemy mapper
from a2a_mesh.agents.echo import build_echo_routes
from a2a_mesh.api.a2a.dispatch import router as dispatch_router
from a2a_mesh.api.v1.agents import router as agents_router
from a2a_mesh.api.v1.auth import router as auth_router
from a2a_mesh.api.v1.runtime import router as runtime_router
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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return our error format directly instead of FastAPI's {"detail": ...} wrapper."""
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(runtime_router)

# Echo agent routes registered before dispatch so static /a2a/echo/ takes priority
_card_routes, _rpc_routes = build_echo_routes()
add_a2a_routes_to_fastapi(app, agent_card_routes=_card_routes, jsonrpc_routes=_rpc_routes)

# Dynamic dispatch — must come after any static /a2a/* routes
app.include_router(dispatch_router)


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

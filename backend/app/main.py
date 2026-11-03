from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.api.routers import sessions, prereq, planning, weekly
from app.routes import (
    project_routes, dashboard_routes, user_routes, agent_routes, auth_routes,
    classroom_routes, notification_routes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Teacher Agent API — startup")
    from app.persistence import load_store
    from app import classroom as _cls
    loaded = load_store()
    if not loaded:
        # First run — no store file yet, seed demo data
        _cls._seed_if_empty()
    yield
    logger.info("AI Teacher Agent API — shutdown")


app = FastAPI(
    title="AI Teacher Agent",
    description="Personalised project-based learning platform powered by LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

_allowed_origins = ["http://localhost:3000"]
_frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router,       prefix="/auth",      tags=["Auth"])
app.include_router(classroom_routes.router,  prefix="/classes",   tags=["Classrooms"])
app.include_router(sessions.router,          prefix="/sessions",  tags=["Sessions"])
app.include_router(prereq.router,            prefix="/prereq",    tags=["Prerequisite"])
app.include_router(planning.router,          prefix="/planning",  tags=["Planning"])
app.include_router(weekly.router,            prefix="/weekly",    tags=["Weekly"])
app.include_router(project_routes.router,    prefix="/projects",  tags=["Projects"])
app.include_router(user_routes.router,       prefix="/users",     tags=["Users"])
app.include_router(dashboard_routes.router,  prefix="/dashboard", tags=["Dashboard"])
app.include_router(notification_routes.router, prefix="/notifications", tags=["Notifications"])
app.include_router(agent_routes.router,      prefix="/agents",    tags=["Agents (debug)"])


@app.get("/", tags=["Health"])
def root():
    return {
        "name":    "AI Teacher Agent",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/health",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
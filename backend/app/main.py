from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.config import APP_ENV, CORS_ORIGIN_REGEX, CORS_ORIGINS
from backend.app.database import Base, SessionLocal, engine, get_db, get_db_backend_name
from backend.app.routers import (
    checks,
    dashboard,
    files,
    glossary,
    issues,
    reports,
    settings,
    team,
)
from backend.app.routers.team import seed_default_team
from backend.app.services.glossary_service import seed_default_glossary


def init_db_and_seeds() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_default_glossary(db)
        seed_default_team(db)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db_and_seeds()
    yield


app = FastAPI(
    title="Qazaq Loc QA API",
    description="Қазақша және өзбекше мобильді ойындар локализациясының сапасын тексеру платформасы",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-LocQA-Modified-Keys", "X-LocQA-Human-Verified"],
)

app.include_router(dashboard.router)
app.include_router(checks.router)
app.include_router(files.router)
app.include_router(issues.router)
app.include_router(glossary.router)
app.include_router(reports.router)
app.include_router(team.router)
app.include_router(settings.router)


@app.get("/")
def root_status():
    return {
        "service": "Qazaq Loc QA API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "platform": "Qazaq Loc QA",
        "version": "1.0.0",
        "environment": APP_ENV,
        "database": get_db_backend_name(),
    }

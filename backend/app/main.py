from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app import db
from app.config import settings
from app.routers import days, demo, health, insights, surveys, today, users
from scripts.seed import seed_if_empty

DESCRIPTION = """
Turns watch data and a daily wellness survey into answers to
"why did I feel bad today?".

There is no auth: pick a persona from `GET /api/users` and pass its id in the path.
Day labels are `good`, `neutral` or `bad`, and `null` when the survey is missing.
"""

TAGS = [
    {"name": "users", "description": "Demo personas (persona switcher)."},
    {"name": "today", "description": "Home screen: heads-up and good signs for today."},
    {"name": "days", "description": "Wellness calendar and day view."},
    {"name": "insights", "description": "Bad day patterns and the good day recipe."},
    {"name": "surveys", "description": "Daily wellness survey (4 sliders, 1-5)."},
    {"name": "demo", "description": "Demo helpers (reset after a live demo)."},
    {"name": "health", "description": "Liveness check."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    db.init_db(db.engine)
    with Session(db.engine) as session:
        seed_if_empty(session)
    yield


app = FastAPI(
    title="Why Today API",
    version="0.1.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (users.router, today.router, days.router, insights.router, surveys.router):
    app.include_router(router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(health.router, prefix="/api")

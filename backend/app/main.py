from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app import db
from app.config import settings
from app.routers import health, items
from scripts.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    db.init_db(db.engine)
    with Session(db.engine) as session:
        seed_if_empty(session)
    yield


app = FastAPI(title="Hackathon API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(items.router, prefix="/api")

from __future__ import annotations

from typing import Dict

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from lakers_optimizer.db import SessionLocal, engine
from lakers_optimizer.ingest import init_db
from lakers_optimizer.optimizer import LineupOptimizer
from lakers_optimizer.schemas import OptimizeLineupRequest, OptimizeLineupResponse, PlayerListResponse


init_db(engine)
app = FastAPI(title="Lakers Lineup Optimization MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/optimize-lineup", response_model=OptimizeLineupResponse)
def optimize_lineup(
    request: OptimizeLineupRequest,
    session: Session = Depends(get_db),
) -> OptimizeLineupResponse:
    optimizer = LineupOptimizer(session=session)
    return optimizer.optimize(request)


@app.get("/players", response_model=PlayerListResponse)
def list_players(session: Session = Depends(get_db)) -> PlayerListResponse:
    optimizer = LineupOptimizer(session=session)
    return optimizer.list_players()

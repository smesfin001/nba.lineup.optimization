from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Tuple

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Player(Base):
    __tablename__ = "players"

    player_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    team = Column(String, nullable=False, index=True)
    position = Column(String, default="", nullable=False)
    height_inches = Column(Integer)
    weight = Column(Integer)
    three_pct = Column(Float)
    ts_pct = Column(Float)
    ast_pct = Column(Float)
    usage_rate = Column(Float)
    games_played = Column(Integer)
    minutes_per_game = Column(Float)
    def_rating = Column(Float)
    dbpm = Column(Float)
    bpm = Column(Float)
    vorp = Column(Float)


class TeamRosterSnapshot(Base):
    __tablename__ = "team_roster_snapshots"
    __table_args__ = (UniqueConstraint("team", "snapshot_date", "player_id", name="uq_team_snapshot_player"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    team = Column(String, index=True, nullable=False)
    snapshot_date = Column(Date, nullable=False)
    player_id = Column(Integer, nullable=False, index=True)


class Lineup(Base):
    __tablename__ = "lineups"
    __table_args__ = (
        UniqueConstraint(
            "player_1_id",
            "player_2_id",
            "player_3_id",
            "player_4_id",
            "player_5_id",
            name="uq_lineup_players",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team = Column(String, nullable=False, index=True)
    player_1_id = Column(Integer, nullable=False)
    player_2_id = Column(Integer, nullable=False)
    player_3_id = Column(Integer, nullable=False)
    player_4_id = Column(Integer, nullable=False)
    player_5_id = Column(Integer, nullable=False)
    shooting_score = Column(Float, nullable=False)
    spacing_score = Column(Float, nullable=False)
    defense_score = Column(Float, nullable=False)
    size_score = Column(Float, nullable=False)
    playmaking_score = Column(Float, nullable=False)
    rotation_score = Column(Float, default=0.0, nullable=False)
    net_rating = Column(Float)
    offensive_rating = Column(Float)
    defensive_rating = Column(Float)
    minutes_played = Column(Integer, default=0, nullable=False)
    trust_score = Column(Float, default=0.0, nullable=False)
    historical_seen = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    @property
    def player_ids(self) -> Tuple[int, int, int, int, int]:
        return (
            self.player_1_id,
            self.player_2_id,
            self.player_3_id,
            self.player_4_id,
            self.player_5_id,
        )

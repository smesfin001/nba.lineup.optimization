from __future__ import annotations

from datetime import date
from typing import Dict, List

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from lakers_optimizer.models import Lineup, Player, TeamRosterSnapshot
from lakers_optimizer.scoring import canonicalize_lineup


class PlayerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_players(self, players: List[dict]) -> int:
        count = 0
        for payload in players:
            player = self.session.get(Player, payload["player_id"])
            if player is None:
                player = Player(**payload)
                self.session.add(player)
            else:
                for key, value in payload.items():
                    setattr(player, key, value)
            count += 1
        self.session.flush()
        return count

    def delete_missing_team_players(self, team: str, keep_player_ids: List[int]) -> int:
        statement = delete(Player).where(Player.team == team)
        if keep_player_ids:
            statement = statement.where(~Player.player_id.in_(keep_player_ids))
        result = self.session.execute(statement)
        self.session.flush()
        return int(result.rowcount or 0)

    def get_players(self, player_ids: List[int]) -> List[Player]:
        statement = select(Player).where(Player.player_id.in_(player_ids))
        result = self.session.execute(statement)
        return list(result.scalars())

    def map_names(self, player_ids: List[int]) -> Dict[int, str]:
        return {player.player_id: player.name for player in self.get_players(player_ids)}

    def list_players(self, team: str) -> List[Player]:
        statement = select(Player).where(Player.team == team).order_by(Player.name.asc())
        result = self.session.execute(statement)
        return list(result.scalars())


class RosterRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_snapshot(self, team: str, snapshot_date: date, player_ids: List[int]) -> None:
        self.session.execute(
            delete(TeamRosterSnapshot).where(
                TeamRosterSnapshot.team == team, TeamRosterSnapshot.snapshot_date == snapshot_date
            )
        )
        for player_id in sorted(set(player_ids)):
            self.session.add(TeamRosterSnapshot(team=team, snapshot_date=snapshot_date, player_id=player_id))
        self.session.flush()

    def delete_team_snapshots(self, team: str) -> int:
        result = self.session.execute(delete(TeamRosterSnapshot).where(TeamRosterSnapshot.team == team))
        self.session.flush()
        return int(result.rowcount or 0)


class LineupRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_lineup(self, payload: dict) -> Lineup:
        player_ids = canonicalize_lineup(payload["player_ids"])
        statement = select(Lineup).where(
            Lineup.player_1_id == player_ids[0],
            Lineup.player_2_id == player_ids[1],
            Lineup.player_3_id == player_ids[2],
            Lineup.player_4_id == player_ids[3],
            Lineup.player_5_id == player_ids[4],
            Lineup.team == payload["team"],
        )
        result = self.session.execute(statement)
        lineup = result.scalars().first()
        if lineup is None:
            lineup = Lineup(
                team=payload["team"],
                player_1_id=player_ids[0],
                player_2_id=player_ids[1],
                player_3_id=player_ids[2],
                player_4_id=player_ids[3],
                player_5_id=player_ids[4],
                shooting_score=payload["shooting_score"],
                spacing_score=payload["spacing_score"],
                defense_score=payload["defense_score"],
                size_score=payload["size_score"],
                playmaking_score=payload["playmaking_score"],
                rotation_score=payload["rotation_score"],
                net_rating=payload.get("net_rating"),
                offensive_rating=payload.get("offensive_rating"),
                defensive_rating=payload.get("defensive_rating"),
                minutes_played=payload.get("minutes_played", 0),
                trust_score=payload["trust_score"],
                historical_seen=payload.get("historical_seen", False),
            )
            self.session.add(lineup)
        else:
            for key, value in payload.items():
                if key == "player_ids":
                    continue
                setattr(lineup, key, value)
        self.session.flush()
        return lineup

    def delete_team_lineups(self, team: str) -> int:
        result = self.session.execute(delete(Lineup).where(Lineup.team == team))
        self.session.flush()
        return int(result.rowcount or 0)

    def list_lineups(self, team: str) -> List[Lineup]:
        statement = select(Lineup).where(Lineup.team == team)
        result = self.session.execute(statement)
        return list(result.scalars())

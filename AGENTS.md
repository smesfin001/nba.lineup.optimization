# AGENTS.md

## Purpose
- This repo is a local MVP for Lakers lineup recommendation.
- The app is FastAPI + SQLite with precomputed lineup scoring.
- Prefer improving the existing pipeline instead of creating parallel paths.

## Current Data Flow
- Player import file: `data/players_import.csv`
- Lineup import file: `data/lineups_import.csv`
- Raw pasted source files:
  - `data/lakers_roster_from_text.csv`
  - `data/lineups_from_text.csv`
- Main rebuild path:
  - delete `lakers_optimizer.db` for a full clean run
  - create metadata with SQLAlchemy
  - load file data source
  - run `ingest_team_snapshot(...)`
  - do not use seed/demo data; CSV import is the source of truth

## Import Schema
- `players_import.csv` columns:
  - `player_id,name,team,position,height_inches,weight,three_pct,ts_pct,ast_pct,usage_rate,games_played,minutes_per_game,def_rating,dbpm,bpm,vorp`
- `lineups_import.csv` columns:
  - `team,player_ids,net_rating,offensive_rating,defensive_rating,minutes_played`
- `player_id` is currently synthetic and based on jersey number for this local dataset.

## Important Modeling Rules
- Non-shooters are currently explicit by name in `lakers_optimizer/scoring.py`:
  - Deandre Ayton
  - Jaxson Hayes
  - Adou Thiero
  - Jarred Vanderbilt
- Do not revert to raw `3P% < threshold` for real players unless asked.
- Optimizer behavior is historical-first:
  - use historical satisfying lineups if any exist
  - fall back to generated lineups only when no historical lineup fits constraints
- Final ranking currently blends:
  - weighted feature fit
  - historical lineup quality/trust
  - lineup rotation score

## Rotation Logic
- Player rotation signal comes from:
  - `games_played`
  - `minutes_per_game`
- Unknown rotation values default low on purpose.
- `rotation_score` is precomputed onto each lineup during ingestion.
- If recommendations still overuse fringe players, adjust rotation weighting or add a hard MPG filter.

## Known Product Gaps
- API supports `must_include`, not native `must_include_any`.
- For `LeBron OR Luka` style asks, current workaround is two queries plus merge.
- Explanation layer is fallback text unless a live OpenAI key is configured.
- Local sandbox may block binding a live localhost server; `TestClient` works reliably for verification.

## Data Caveats
- Historical lineup data is partial and came from pasted text, not full NBA Stats export.
- Many advanced player fields may still be blank unless manually supplied.
- If user provides updated player stats, update `players_import.csv` directly and rebuild the DB.
- If roster changes, remove stale players and stale lineups explicitly before reimporting.

## Full Clean Run
- Backend clean rebuild:
  - `rm -f lakers_optimizer.db`
  - `python3 -m lakers_optimizer.cli init-db`
  - `python3 -m lakers_optimizer.cli import-data --players-file data/players_import.csv --lineups-file data/lineups_import.csv --team LAL`
- Verification:
  - `python3 -m lakers_optimizer.cli optimize --query "Need defense and shooting" --must-include 23 --limit 3`
- Frontend:
  - `cd frontend && npm install && npm run dev`

## Useful Verification Commands
- `python3 -m pytest tests/test_scoring.py -q`
- `python3 -m lakers_optimizer.cli optimize --query "Need defense and shooting" --must-include 23 --limit 3`
- In-process API check:
  - use `fastapi.testclient.TestClient`
  - avoid assuming `uvicorn` bind will work in the sandbox

## Editing Guidance
- Keep changes local and pragmatic.
- Prefer fixing the scoring/data model over adding prompt hacks.
- If recommendations look wrong, inspect:
  - non-shooter logic
  - historical candidate availability
  - imported player GP/MPG data
  - persisted lineup `rotation_score`

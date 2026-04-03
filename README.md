# Lakers Lineup Optimization MVP

FastAPI + SQLite MVP for precomputed lineup recommendation.

## Quick start

```bash
python3 -m pip install -e ".[dev]"
rm -f lakers_optimizer.db
python3 -m lakers_optimizer.cli init-db
python3 -m lakers_optimizer.cli import-data --players-file data/players_import.csv --lineups-file data/lineups_import.csv --team LAL
python3 -m uvicorn lakers_optimizer.api:app --reload
pytest
```

If `data/lakers_roster_from_text.csv` exists, the CLI automatically merges it as player metadata (games, minutes, usage, etc.). Override the path with `--metadata-file`.

## Full clean run

Use this when you want to rebuild from CSVs only and guarantee no stale local DB data survives:

```bash
cd /Users/sammesfin/Lakers/nba.lineup.optimization
python3 -m pip install -e ".[dev]"
rm -f lakers_optimizer.db
python3 -m lakers_optimizer.cli init-db
python3 -m lakers_optimizer.cli import-data \
  --players-file data/players_import.csv \
  --lineups-file data/lineups_import.csv \
  --team LAL
python3 -m lakers_optimizer.cli optimize --query "Need defense and shooting" --must-include 23 --limit 3
python3 -m uvicorn lakers_optimizer.api:app --reload
```

By default the import command pulls `data/lakers_roster_from_text.csv` as additional metadata; set `--metadata-file` if you need to point somewhere else.

If you also want a clean frontend run:

```bash
cd /Users/sammesfin/Lakers/nba.lineup.optimization/frontend
npm install
npm run dev
```

## Run with uv and CSV data

Backend terminal:

```bash
cd /Users/sammesfin/Lakers/nba.lineup.optimization
export PATH="$HOME/.local/bin:$PATH"
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
rm -f lakers_optimizer.db
python -m lakers_optimizer.cli init-db
python -m lakers_optimizer.cli import-data \
  --players-file data/players_import.csv \
  --lineups-file data/lineups_import.csv \
  --team LAL
python -m uvicorn lakers_optimizer.api:app --reload
```

Clean rebuild summary:

- delete `lakers_optimizer.db`
- import from `data/players_import.csv` and `data/lineups_import.csv`
- do not use any seed/demo command; CSV import is the only supported rebuild path

Frontend terminal:

```bash
cd /Users/sammesfin/Lakers/nba.lineup.optimization
source "$HOME/.nvm/nvm.sh"
nvm use 20
cd frontend
npm install
npm run dev
```

Open:

- `http://127.0.0.1:5173`
- `http://127.0.0.1:8000/docs`

Quick verification:

```bash
cd /Users/sammesfin/Lakers/nba.lineup.optimization
source .venv/bin/activate
python -m lakers_optimizer.cli optimize --query "Need defense and shooting" --must-include 23 --limit 3
```

## File import

Import either a bundled JSON file:

```bash
python3 -m lakers_optimizer.cli import-data --bundle-file data/lakers_bundle.json --team LAL --date 2026-04-02
```

Or separate player and lineup files:

```bash
python3 -m lakers_optimizer.cli import-data --players-file data/players.csv --lineups-file data/lineups.csv --team LAL
```

Use `--metadata-file data/lakers_roster_from_text.csv` (or another CSV) when you want to merge the roster metadata outside of the default location.

Supported formats:

- `players.csv` or `players.json`: `player_id,name,team,position,height_inches,weight,three_pct,ts_pct,ast_pct,usage_rate,games_played,minutes_per_game,def_rating,dbpm,bpm,vorp`
- `lineups.csv` or `lineups.json`: `team,player_ids,net_rating,offensive_rating,defensive_rating,minutes_played[,games_played]`
  - `minutes_played` should be the per-game value. If you also provide `games_played`, the import multiplies the two to derive the stored total minutes (used for trust and display); without `games_played`, the supplied `minutes_played` is treated as the total.
- `player_ids` may be a JSON array in `.json` or a comma-separated string in `.csv`
- bundle JSON shape:

```json
{
  "players": [
    {
      "player_id": 23,
      "name": "LeBron James",
      "team": "LAL"
    }
  ],
  "lineups": [
    {
      "team": "LAL",
      "player_ids": [23, 3, 15, 12, 28],
      "minutes_played": 180
    }
  ]
}
```

## Environment

- `LAKERS_DB_URL` defaults to `sqlite:///./lakers_optimizer.db`
- `OPENAI_API_KEY` enables live query parsing and explanation generation
- `OPENAI_MODEL` defaults to `gpt-4.1-mini`

Without an API key, the app uses deterministic fallback parsing and explanations so the optimization path still works.

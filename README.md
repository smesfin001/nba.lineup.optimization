# Lakers Lineup Optimization MVP

FastAPI + SQLite MVP for precomputed lineup recommendation.

## Quick start

```bash
#Optional: Use this to enable LLM query parsing
export OPENAI_API_KEY=<API_KEY>

python3 -m pip install -e ".[dev]"
# Remove the db when you want to rebuild from CSVs only and guarantee no stale local DB data survives
rm -f lakers_optimizer.db
python3 -m lakers_optimizer.cli init-db
python3 -m lakers_optimizer.cli import-data \
  --players-file data/players_import.csv \
  --lineups-file data/lineups_import.csv \
  --team LAL
python3 -m lakers_optimizer.cli optimize --query "Need defense and shooting" --must-include 23 --limit 3
python3 -m uvicorn lakers_optimizer.api:app --reload
```

## Verification

Run this query to verify 3 optimized lineups for defense and shooting, with Lebron included in all lineups.

```bash
python3 -m lakers_optimizer.cli optimize --query "Need defense and shooting" --must-include 23 --limit 3
```

## Run Tests

```bash
pytest
```

## Environment

- `LAKERS_DB_URL` defaults to `sqlite:///./lakers_optimizer.db`
- `OPENAI_API_KEY` enables live query parsing and explanation generation
- `OPENAI_MODEL` defaults to `gpt-4.1-mini`

Without an API key, the app uses deterministic fallback parsing and explanations so the optimization path still works.

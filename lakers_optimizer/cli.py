from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from pprint import pprint

from lakers_optimizer.db import engine, session_scope
from lakers_optimizer.ingest import ingest_team_snapshot, init_db, load_file_data_source
from lakers_optimizer.optimizer import LineupOptimizer
from lakers_optimizer.schemas import OptimizeLineupRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lakers lineup optimization CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db")

    import_data = subparsers.add_parser("import-data")
    import_data.add_argument("--team", default="LAL")
    import_data.add_argument("--date", default=str(date.today()))
    import_data.add_argument("--players-file")
    import_data.add_argument("--lineups-file")
    import_data.add_argument("--bundle-file")
    import_data.add_argument("--metadata-file")

    optimize = subparsers.add_parser("optimize")
    optimize.add_argument("--query", required=True)
    optimize.add_argument("--team", default="LAL")
    optimize.add_argument("--must-include", nargs="*", type=int, default=[])
    optimize.add_argument("--limit", type=int, default=5)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        init_db(engine)
        print("Initialized database schema.")
        return

    if args.command == "import-data":
        if not args.bundle_file and not args.players_file:
            parser.error("import-data requires --bundle-file or --players-file")
        metadata_file = args.metadata_file
        if metadata_file is None:
            default_metadata = Path("data/lakers_roster_from_text.csv")
            if default_metadata.exists():
                metadata_file = str(default_metadata)
        source = load_file_data_source(
            players_path=args.players_file,
            lineups_path=args.lineups_file,
            bundle_path=args.bundle_file,
            metadata_path=metadata_file,
            team=args.team,
        )
        init_db(engine)
        with session_scope() as session:
            summary = ingest_team_snapshot(
                session,
                team=args.team,
                snapshot_date=date.fromisoformat(args.date),
                source=source,
            )
        pprint(summary.model_dump())
        return

    if args.command == "optimize":
        with session_scope() as session:
            optimizer = LineupOptimizer(session=session)
            response = optimizer.optimize(
                OptimizeLineupRequest(
                    query=args.query,
                    limit=args.limit,
                    constraints={"must_include": args.must_include},
                )
            )
        pprint(response.model_dump())
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()

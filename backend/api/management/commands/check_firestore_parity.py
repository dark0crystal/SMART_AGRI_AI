from __future__ import annotations

import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from api.firestore_repository import export_collection_ids

TABLE_TO_COLLECTION = {
    "users": "users",
    "plants": "plants",
    "diseases": "diseases",
    "diagnoses": "diagnoses",
    "ai_logs": "ai_logs",
    "reviews": "reviews",
}


class Command(BaseCommand):
    help = "Compare row counts between legacy SQLite and Firestore collections."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sqlite-path",
            default=str(Path(settings.BASE_DIR) / "db.sqlite3"),
            help="Path to SQLite file used as baseline.",
        )

    def handle(self, *args, **options):
        db_path = Path(options["sqlite_path"]).expanduser()
        if not db_path.exists():
            raise CommandError(f"SQLite file not found: {db_path}")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        has_mismatch = False
        try:
            for table, collection in TABLE_TO_COLLECTION.items():
                sqlite_count = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
                firestore_count = len(export_collection_ids(collection))
                state = "OK" if sqlite_count == firestore_count else "MISMATCH"
                if state == "MISMATCH":
                    has_mismatch = True
                self.stdout.write(
                    f"{state}: {table}={sqlite_count} vs {collection}={firestore_count}"
                )
        finally:
            conn.close()

        if has_mismatch:
            raise CommandError("Parity check failed: one or more collections are out of sync.")
        self.stdout.write(self.style.SUCCESS("Parity check passed for all mapped tables."))

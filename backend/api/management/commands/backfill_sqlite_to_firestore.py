from __future__ import annotations

import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from api.firestore_repository import write_raw_document


TABLE_TO_COLLECTION = {
    "users": "users",
    "plants": "plants",
    "diseases": "diseases",
    "diagnoses": "diagnoses",
    "ai_logs": "ai_logs",
    "reviews": "reviews",
}


class Command(BaseCommand):
    help = "One-time migration: copy existing SQLite rows into Firestore."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sqlite-path",
            default=str(Path(settings.BASE_DIR) / "db.sqlite3"),
            help="Path to SQLite database file (default: backend/db.sqlite3).",
        )

    def handle(self, *args, **options):
        db_path = Path(options["sqlite_path"]).expanduser()
        if not db_path.exists():
            raise CommandError(f"SQLite file not found: {db_path}")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            for table, collection in TABLE_TO_COLLECTION.items():
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                for row in rows:
                    data = dict(row)
                    doc_id = str(data.get("id"))
                    if not doc_id or doc_id == "None":
                        continue
                    if table == "diseases":
                        data["plant_id"] = data.get("plant_id")
                    if table == "diagnoses":
                        data["user_id"] = data.get("user_id")
                        data["disease_id"] = data.get("disease_id")
                    if table == "ai_logs":
                        data["diagnosis_id"] = data.get("diagnosis_id")
                    if table == "reviews":
                        data["user_id"] = data.get("user_id")
                        data["diagnosis_id"] = data.get("diagnosis_id")
                    write_raw_document(collection=collection, doc_id=doc_id, data=data)
                self.stdout.write(f"Migrated {len(rows)} rows from {table} -> {collection}")
        finally:
            conn.close()

        self.stdout.write(self.style.SUCCESS("SQLite to Firestore backfill complete."))

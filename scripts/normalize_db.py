from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from text_normalizer import normalize_text

FIELDS = {
    "epis": ["epi", "descricao", "normas"],
    "perigos": ["perigo", "consequencias", "salvaguardas"],
    "aprs": [
        "titulo",
        "risco",
        "descricao",
        "worksite",
        "sector",
        "responsible",
        "activity_id",
        "activity_name",
    ],
    "passos": [
        "descricao",
        "perigos",
        "riscos",
        "medidas_controle",
        "epis",
        "normas",
    ],
}


def normalize_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    table_updates = {}
    field_updates = {}

    for table, fields in FIELDS.items():
        cur.execute(f"SELECT id, {', '.join(fields)} FROM {table}")
        rows = cur.fetchall()
        for row in rows:
            row_id = row[0]
            updates = {}
            for idx, field in enumerate(fields, start=1):
                value = row[idx]
                if value is None:
                    continue
                normalized = normalize_text(
                    value,
                    origin="cleanup",
                    field=f"{table}.{field}",
                )
                if normalized != value:
                    updates[field] = normalized
                    field_updates[(table, field)] = field_updates.get((table, field), 0) + 1
            if updates:
                sets = ", ".join([f"{col} = ?" for col in updates.keys()])
                params = list(updates.values()) + [row_id]
                cur.execute(f"UPDATE {table} SET {sets} WHERE id = ?", params)
                table_updates[table] = table_updates.get(table, 0) + 1

    conn.commit()
    conn.close()

    print("normalize_db: done")
    for table in sorted(table_updates.keys()):
        print(f"- {table}: {table_updates[table]} rows updated")
    if not table_updates:
        print("- no changes")
    if field_updates:
        print("field updates:")
        for (table, field), count in sorted(field_updates.items()):
            print(f"  {table}.{field}: {count}")


if __name__ == "__main__":
    db_path = BASE_DIR / "app.db"
    if not db_path.exists():
        raise SystemExit(f"db not found: {db_path}")
    normalize_db(db_path)

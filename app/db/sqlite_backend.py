"""SQLite storage backend."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from app.db.migrations import get_all_create_sql


class SQLiteBackend:
    """SQLite-based storage with WAL mode and JSON provenance columns."""

    def __init__(self, database_path: str = ":memory:") -> None:
        self._db_path = database_path
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            if self._db_path != ":memory:":
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize(self) -> None:
        conn = self._connect()
        for sql in get_all_create_sql():
            conn.execute(sql)
        conn.commit()

    def is_ready(self) -> bool:
        try:
            conn = self._connect()
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def save_record(self, table: str, record: dict[str, Any]) -> None:
        conn = self._connect()
        # Serialize dicts/lists as JSON
        processed = {}
        for k, v in record.items():
            if isinstance(v, (dict, list)):
                processed[k] = json.dumps(v)
            else:
                processed[k] = v

        columns = ", ".join(processed.keys())
        placeholders = ", ".join("?" for _ in processed)
        values = list(processed.values())

        conn.execute(
            f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
            values,
        )
        conn.commit()

    def get_record(self, table: str, record_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        # Determine primary key column (first column)
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        if not columns:
            return None
        pk_col = columns[0]["name"]

        row = conn.execute(
            f"SELECT * FROM {table} WHERE {pk_col} = ?", (record_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def list_records(
        self,
        table: str,
        project_id: str | None = None,
        patient_id: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conn = self._connect()
        conditions: list[str] = []
        params: list[Any] = []
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if patient_id:
            conditions.append("patient_id = ?")
            params.append(patient_id)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM {table}{where} LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def execute_sql(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        conn = self._connect()
        cursor = conn.execute(sql, params or ())
        if cursor.description is None:
            conn.commit()
            return []
        return [dict(r) for r in cursor.fetchall()]

    def export_csv(self, table: str, output_path: str, project_id: str | None = None) -> int:
        records = self.list_records(table, project_id=project_id, limit=999999)
        if not records:
            return 0
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        return len(records)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

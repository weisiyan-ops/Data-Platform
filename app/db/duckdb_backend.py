"""DuckDB storage backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from app.db.migrations import get_all_create_sql


class DuckDBBackend:
    """DuckDB-based storage — columnar, fast analytical queries, Parquet export."""

    def __init__(self, database_path: str = ":memory:") -> None:
        self._db_path = database_path
        self._conn: duckdb.DuckDBPyConnection | None = None

    def _connect(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            if self._db_path != ":memory:":
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(self._db_path)
        return self._conn

    def initialize(self) -> None:
        conn = self._connect()
        for sql in get_all_create_sql():
            conn.execute(sql)

    def is_ready(self) -> bool:
        try:
            conn = self._connect()
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def save_record(self, table: str, record: dict[str, Any]) -> None:
        conn = self._connect()
        processed = {}
        for k, v in record.items():
            if isinstance(v, (dict, list)):
                processed[k] = json.dumps(v)
            else:
                processed[k] = v

        columns = ", ".join(processed.keys())
        placeholders = ", ".join("$" + str(i + 1) for i in range(len(processed)))
        values = list(processed.values())

        # DuckDB uses INSERT OR REPLACE via INSERT OR REPLACE INTO
        conn.execute(
            f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
            values,
        )

    def get_record(self, table: str, record_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        # Get first column name as PK
        info = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
        if not info:
            return None
        pk_col = info[0][1]

        result = conn.execute(
            f"SELECT * FROM {table} WHERE {pk_col} = $1", [record_id]
        )
        columns = [desc[0] for desc in result.description]
        row = result.fetchone()
        if row is None:
            return None
        return dict(zip(columns, row))

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
        idx = 1
        if project_id:
            conditions.append(f"project_id = ${idx}")
            params.append(project_id)
            idx += 1
        if patient_id:
            conditions.append(f"patient_id = ${idx}")
            params.append(patient_id)
            idx += 1

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])
        result = conn.execute(
            f"SELECT * FROM {table}{where} LIMIT ${idx} OFFSET ${idx + 1}",
            params,
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def execute_sql(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        conn = self._connect()
        result = conn.execute(sql, list(params) if params else [])
        if result.description is None:
            return []
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def export_csv(self, table: str, output_path: str, project_id: str | None = None) -> int:
        conn = self._connect()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if project_id:
            conn.execute(
                f"COPY (SELECT * FROM {table} WHERE project_id = $1) TO '{output_path}' (HEADER, DELIMITER ',')",
                [project_id],
            )
        else:
            conn.execute(
                f"COPY {table} TO '{output_path}' (HEADER, DELIMITER ',')"
            )
        # Count rows exported
        if project_id:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE project_id = $1", [project_id]
            ).fetchone()
        else:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return count[0] if count else 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

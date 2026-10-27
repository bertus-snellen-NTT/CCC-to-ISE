import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def save_catalyst_center_run(
    database_path: Path, clients: list[dict]
) -> dict:
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _initialize_schema(connection)
        cursor = connection.execute(
            """
            INSERT INTO catalyst_center_runs (captured_at, record_count)
            VALUES (?, ?)
            """,
            (captured_at, len(clients)),
        )
        run_id = cursor.lastrowid
        connection.executemany(
            """
            INSERT INTO catalyst_center_clients (
                run_id, mac_address, ipv4_address, vendor,
                connection_status, last_update_time, client_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    _value(client, "macAddress"),
                    _value(client, "ipv4Address"),
                    _value(client, "vendor"),
                    _first_value(client, "connectionStatus", "connectioSatus"),
                    _first_value(
                        client, "LastUpdateTime", "lastUpdateTime", "lastUpdated"
                    ),
                    json.dumps(client),
                )
                for client in clients
            ],
        )

    return {
        "id": run_id,
        "capturedAt": captured_at,
        "recordCount": len(clients),
    }


def get_catalyst_center_data(database_path: Path) -> dict:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        _initialize_schema(connection)
        runs = [
            dict(row)
            for row in connection.execute(
                """
                SELECT id, captured_at, record_count
                FROM catalyst_center_runs
                ORDER BY id DESC
                """
            )
        ]
        latest_clients = []
        if runs:
            latest_clients = [
                {
                    "macAddress": row["mac_address"],
                    "ipv4Address": row["ipv4_address"],
                    "vendor": row["vendor"],
                    "connectionStatus": row["connection_status"],
                    "lastUpdateTime": row["last_update_time"],
                    "data": json.loads(row["client_json"]),
                }
                for row in connection.execute(
                    """
                    SELECT mac_address, ipv4_address, vendor, connection_status,
                           last_update_time, client_json
                    FROM catalyst_center_clients
                    WHERE run_id = ?
                    ORDER BY id
                    """,
                    (runs[0]["id"],),
                )
            ]

    return {
        "latest_run": runs[0] if runs else None,
        "runs": runs,
        "clients": latest_clients,
    }


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS catalyst_center_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at TEXT NOT NULL,
            record_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS catalyst_center_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL REFERENCES catalyst_center_runs(id),
            mac_address TEXT,
            ipv4_address TEXT,
            vendor TEXT,
            connection_status TEXT,
            last_update_time TEXT,
            client_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS catalyst_center_clients_run_id
            ON catalyst_center_clients(run_id);
        """
    )


def _value(client: dict, key: str) -> Optional[str]:
    value = client.get(key)
    if isinstance(value, (str, int, float)):
        return str(value)
    return None


def _first_value(client: dict, *keys: str) -> Optional[str]:
    for key in keys:
        value = _value(client, key)
        if value is not None:
            return value
    return None

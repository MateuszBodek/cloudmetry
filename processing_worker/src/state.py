from __future__ import annotations

import logging
from datetime import datetime

import pyarrow as pa
from deltalake import DeltaTable

from .config import Settings, create_duckdb_connection
from .delta_ops import is_delta_table, merge_delta

LOGGER = logging.getLogger("processing_worker")


def list_unprocessed_files(settings: Settings) -> list[str]:
    connection = create_duckdb_connection(settings)
    try:
        connection.execute("SELECT file FROM glob(?)", [settings.bronze_glob])
        discovered = sorted({row[0] for row in connection.fetchall()})
        if not discovered:
            return []

        if not is_delta_table(settings.state_table, settings):
            return discovered

        processed_table = DeltaTable(
            settings.state_table, storage_options=settings.delta_storage_options
        )
        connection.register(
            "processed_files_dataset", processed_table.to_pyarrow_dataset()
        )
        try:
            processed = {
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT source_file FROM processed_files_dataset"
                ).fetchall()
            }
        finally:
            connection.unregister("processed_files_dataset")
        return [path for path in discovered if path not in processed]
    finally:
        connection.close()


def record_processed_files(
    bronze_files: list[str], settings: Settings, run_time: datetime
) -> None:
    if not bronze_files:
        return
    processed = pa.table(
        {
            "source_file": pa.array(bronze_files, type=pa.string()),
            "processed_at": pa.array(
                [run_time] * len(bronze_files), type=pa.timestamp("us", tz="UTC")
            ),
        }
    )
    merge_delta(processed, settings.state_table, ["source_file"], [], settings)

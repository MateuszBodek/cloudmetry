from __future__ import annotations

import logging

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from .config import Settings

LOGGER = logging.getLogger("processing_worker")


def is_delta_table(uri: str, settings: Settings) -> bool:
    return DeltaTable.is_deltatable(uri, storage_options=settings.delta_storage_options)


def merge_delta(
    table: pa.Table,
    uri: str,
    key_columns: list[str],
    partition_columns: list[str],
    settings: Settings,
) -> None:
    if not is_delta_table(uri, settings):
        write_deltalake(
            uri,
            table,
            mode="error",
            partition_by=partition_columns,
            storage_options=settings.delta_storage_options,
        )
        return

    if table.num_rows == 0:
        return
    if not key_columns:
        raise ValueError("At least one key column is required to merge a Delta table")

    target = DeltaTable(uri, storage_options=settings.delta_storage_options)
    predicate = " AND ".join(
        f"target.{column} = source.{column}" for column in key_columns
    )
    (
        target.merge(
            source=table,
            predicate=predicate,
            source_alias="source",
            target_alias="target",
            merge_schema=True,
        )
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute()
    )


def compact_delta(uri: str, settings: Settings) -> None:
    if is_delta_table(uri, settings):
        result = DeltaTable(
            uri, storage_options=settings.delta_storage_options
        ).optimize.compact()
        LOGGER.info("Compacted %s: %s", uri, result)


def reset_legacy_lakehouse_tables(settings: Settings) -> list[str]:
    if not settings.reset_lakehouse_tables:
        return []

    legacy_columns = {
        settings.gps_table: {"data_json", "wind_speed_10m"},
        settings.telemetry_table: {"data_json"},
        settings.accelerometer_table: {"data_json"},
        settings.gold_table: {
            "accelerometer_data_json",
            "gps_data_json",
            "wind_speed_10m",
        },
    }
    legacy_tables = []
    for uri, columns in legacy_columns.items():
        if not is_delta_table(uri, settings):
            continue
        table = DeltaTable(uri, storage_options=settings.delta_storage_options)
        schema = table.to_pyarrow_dataset().schema
        obsolete_columns = columns.intersection(schema.names)
        if obsolete_columns:
            legacy_tables.append((uri, table, schema, obsolete_columns))

    if not legacy_tables:
        return []

    if is_delta_table(settings.state_table, settings):
        DeltaTable(
            settings.state_table, storage_options=settings.delta_storage_options
        ).delete()

    reset_uris = []
    for uri, table, existing_schema, obsolete_columns in legacy_tables:
        clean_schema = pa.schema(
            field for field in existing_schema if field.name not in obsolete_columns
        )
        empty_table = pa.Table.from_batches([], schema=clean_schema)
        write_deltalake(
            uri,
            empty_table,
            mode="overwrite",
            schema_mode="overwrite",
            partition_by=table.metadata().partition_columns,
            storage_options=settings.delta_storage_options,
        )
        reset_uris.append(uri)

    LOGGER.warning(
        "Reset legacy Delta tables containing duplicate JSON columns (%s) and "
        "cleared processed-file state; all Bronze files will be replayed",
        ", ".join(reset_uris),
    )
    return reset_uris

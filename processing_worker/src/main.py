from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dbt.cli.main import dbtRunner

from common.src.logger import setup_logger

from .config import Settings, telemetry_column_names
from .delta_ops import compact_delta, reset_legacy_lakehouse_tables
from .state import list_unprocessed_files, record_processed_files
from .weather import enrich_weather_for_batch

LOGGER = logging.getLogger("processing_worker")
DBT_PROJECT_DIR = Path(__file__).resolve().parents[1] / "dbt_cloudmetry"


def run_dbt(settings: Settings, bronze_files: list[str]) -> None:
    variables = {
        "bronze_files": bronze_files,
        "telemetry_columns": telemetry_column_names(),
        "silver_gps_uri": settings.gps_table,
        "silver_telemetry_uri": settings.telemetry_table,
        "silver_accelerometer_uri": settings.accelerometer_table,
        "silver_weather_uri": settings.weather_table,
        "gold_telemetry_uri": settings.gold_table,
        "gold_drive_summary_uri": settings.gold_drive_summary_table,
        "gold_dim_drive_meta_uri": settings.gold_dim_drive_meta_table,
        "gold_dim_weather_conditions_uri": settings.gold_dim_weather_conditions_table,
        "gold_dim_fuel_profile_uri": settings.gold_dim_fuel_profile_table,
        "gold_dim_thermal_profile_uri": settings.gold_dim_thermal_profile_table,
        "gold_dim_rusefi_error_code_uri": settings.gold_dim_rusefi_error_code_table,
        "dbt_staging_uri": settings.dbt_staging_uri.rstrip("/"),
        "batch_id": uuid4().hex,
    }
    result = dbtRunner().invoke(
        [
            "build",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROJECT_DIR),
            "--profile",
            "cloudmetry",
            "--target",
            "local",
            "--vars",
            json.dumps(variables),
        ]
    )
    if not result.success:
        exception = getattr(result, "exception", None)
        raise RuntimeError(
            "dbt run failed; Bronze files remain eligible to retry"
        ) from exception


def run_pipeline(settings: Settings) -> None:
    try:
        reset_legacy_lakehouse_tables(settings)
        bronze_files = list_unprocessed_files(settings)
        if not bronze_files:
            LOGGER.info("No new Bronze files found")
            return

        LOGGER.info("Processing %d new Bronze files", len(bronze_files))
        enrich_weather_for_batch(bronze_files, settings)
        run_dbt(settings, bronze_files)

        for uri in (
            settings.gps_table,
            settings.telemetry_table,
            settings.accelerometer_table,
            settings.weather_table,
            settings.gold_table,
            settings.gold_drive_summary_table,
            settings.gold_dim_drive_meta_table,
            settings.gold_dim_weather_conditions_table,
            settings.gold_dim_fuel_profile_table,
            settings.gold_dim_thermal_profile_table,
            settings.gold_dim_rusefi_error_code_table,
        ):
            compact_delta(uri, settings)
        record_processed_files(bronze_files, settings, datetime.now(UTC))
        LOGGER.info("ETL completed successfully: %d files", len(bronze_files))
    except Exception:
        LOGGER.exception("Lakehouse ETL failed; Bronze files remain eligible to retry")
        raise


def main() -> None:
    setup_logger("processing_worker")
    run_pipeline(Settings())


if __name__ == "__main__":
    main()

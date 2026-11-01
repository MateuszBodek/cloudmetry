from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import duckdb

TELEMETRY_COLUMNS_PATH = (
    Path(__file__).resolve().parents[2]
    / "car_simulator"
    / "data"
    / "core_telemetry_columns.txt"
)


class Settings:
    """Runtime configuration for the single-writer ETL process."""

    def __init__(self) -> None:
        self.endpoint = os.getenv("S3_ENDPOINT", "http://localhost:8333").rstrip("/")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "cloudmetry-local-access")
        self.secret_key = os.getenv(
            "AWS_SECRET_ACCESS_KEY", "cloudmetry-local-secret-key-change-this"
        )
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bronze_glob = os.getenv(
            "BRONZE_GLOB", "s3://bronze/telemetry/**/*.parquet"
        )
        self.gps_table = os.getenv("SILVER_GPS_URI", "s3://silver/gps")
        self.telemetry_table = os.getenv(
            "SILVER_TELEMETRY_URI", "s3://silver/telemetry"
        )
        self.accelerometer_table = os.getenv(
            "SILVER_ACCELEROMETER_URI", "s3://silver/accelerometer"
        )
        self.weather_table = os.getenv("SILVER_WEATHER_URI", "s3://silver/weather")
        self.state_table = os.getenv(
            "PROCESSED_FILES_URI", "s3://silver/_processed_files"
        )
        self.gold_table = os.getenv("GOLD_TELEMETRY_URI", "s3://gold/drive_telemetry")
        self.gold_drive_summary_table = os.getenv(
            "GOLD_DRIVE_SUMMARY_URI", "s3://gold/fct_drive_summary"
        )
        self.gold_dim_drive_meta_table = os.getenv(
            "GOLD_DIM_DRIVE_META_URI", "s3://gold/dim_drive_meta"
        )
        self.gold_dim_weather_conditions_table = os.getenv(
            "GOLD_DIM_WEATHER_CONDITIONS_URI",
            "s3://gold/dim_weather_conditions",
        )
        self.gold_dim_fuel_profile_table = os.getenv(
            "GOLD_DIM_FUEL_PROFILE_URI", "s3://gold/dim_fuel_profile"
        )
        self.gold_dim_thermal_profile_table = os.getenv(
            "GOLD_DIM_THERMAL_PROFILE_URI", "s3://gold/dim_thermal_profile"
        )
        self.gold_dim_rusefi_error_code_table = os.getenv(
            "GOLD_DIM_RUSEFI_ERROR_CODE_URI", "s3://gold/dim_rusefi_error_code"
        )
        self.dbt_staging_uri = os.getenv("DBT_STAGING_URI", "s3://silver/_dbt_staging")
        self.weather_timeout = float(os.getenv("WEATHER_TIMEOUT_SECONDS", "20"))
        self.weather_attempts = max(1, int(os.getenv("WEATHER_RETRIES", "4")))
        self.duckdb_threads = int(os.getenv("DUCKDB_THREADS", "4"))
        reset_lakehouse_tables = os.getenv(
            "RESET_LAKEHOUSE_TABLES",
            os.getenv("RESET_SILVER_TELEMETRY", "false"),
        ).lower()
        if reset_lakehouse_tables not in {"true", "false"}:
            raise ValueError("RESET_LAKEHOUSE_TABLES must be 'true' or 'false'")
        self.reset_lakehouse_tables = reset_lakehouse_tables == "true"

        if not self.endpoint.startswith(("http://", "https://")):
            raise ValueError("S3_ENDPOINT must start with http:// or https://")
        if self.weather_timeout <= 0:
            raise ValueError("WEATHER_TIMEOUT_SECONDS must be greater than zero")
        if self.duckdb_threads < 1:
            raise ValueError("DUCKDB_THREADS must be at least 1")

        os.environ["AWS_ALLOW_HTTP"] = "true"
        os.environ["AWS_S3_ADDRESSING_STYLE"] = "path"
        os.environ["AWS_S3_ALLOW_UNSAFE_RENAME"] = "true"
        os.environ["CLOUDMETRY_WORKSPACE_ROOT"] = str(
            Path(__file__).resolve().parents[2]
        )

    @property
    def delta_storage_options(self) -> dict[str, str]:
        return {
            "AWS_ACCESS_KEY_ID": self.access_key,
            "AWS_SECRET_ACCESS_KEY": self.secret_key,
            "AWS_REGION": self.region,
            "AWS_ENDPOINT_URL": self.endpoint,
            "AWS_ALLOW_HTTP": "true",
            "AWS_S3_ADDRESSING_STYLE": "path",
            "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
        }


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def create_duckdb_connection(settings: Settings) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    connection.execute("INSTALL httpfs")
    connection.execute("LOAD httpfs")
    connection.execute(f"SET threads = {settings.duckdb_threads}")
    connection.execute("SET preserve_insertion_order = false")

    endpoint = urlparse(settings.endpoint)
    connection.execute(f"SET s3_endpoint = {_sql_string(endpoint.netloc)}")
    connection.execute(
        f"SET s3_use_ssl = {'true' if endpoint.scheme == 'https' else 'false'}"
    )
    connection.execute("SET s3_url_style = 'path'")
    connection.execute(f"SET s3_region = {_sql_string(settings.region)}")
    connection.execute(f"SET s3_access_key_id = {_sql_string(settings.access_key)}")
    connection.execute(f"SET s3_secret_access_key = {_sql_string(settings.secret_key)}")
    return connection


def telemetry_column_names() -> list[str]:
    columns = [
        line.strip()
        for line in TELEMETRY_COLUMNS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    normalized_columns = [
        re.sub(
            r"[^a-z0-9]+",
            "_",
            re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", column).lower(),
        ).strip("_")
        for column in columns
    ]
    if not normalized_columns:
        raise ValueError(f"No telemetry columns configured in {TELEMETRY_COLUMNS_PATH}")
    if len(normalized_columns) != len(set(normalized_columns)):
        raise ValueError(
            f"Duplicate normalized telemetry columns in {TELEMETRY_COLUMNS_PATH}"
        )
    if any(
        not re.fullmatch(r"[a-z][a-z0-9_]*", column) for column in normalized_columns
    ):
        raise ValueError(f"Invalid telemetry column name in {TELEMETRY_COLUMNS_PATH}")
    return normalized_columns

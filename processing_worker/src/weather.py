from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pyarrow as pa
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Settings, create_duckdb_connection
from .delta_ops import merge_delta

LOGGER = logging.getLogger("processing_worker")
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
RECENT_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
WARSAW_TIMEZONE = ZoneInfo("Europe/Warsaw")
WEATHER_KEYS = ["lat_grid", "lon_grid", "hour_bucket"]


def create_weather_session(settings: Settings) -> requests.Session:
    retry = Retry(
        total=settings.weather_attempts,
        connect=settings.weather_attempts,
        read=settings.weather_attempts,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_weather(
    locations: pa.Table, settings: Settings, session: requests.Session
) -> pa.Table:
    weather_by_key: dict[
        tuple[float, float, datetime], tuple[Any, Any, Any, Any, Any]
    ] = {}
    for location in locations.to_pylist():
        latitude = float(location["lat_grid"])
        longitude = float(location["lon_grid"])
        start_date = location["min_date"]
        end_date = location["max_date"]
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        today = datetime.now(WARSAW_TIMEZONE).date()
        recent_forecast_start = today - timedelta(days=5)
        use_recent_forecast = (
            recent_forecast_start <= start_date <= today and end_date <= today
        )
        params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": (
                "temperature_2m,precipitation,surface_pressure,"
                "relative_humidity_2m,wind_speed_10m"
            ),
            "wind_speed_unit": "ms",
            "timezone": "Europe/Warsaw",
        }
        if use_recent_forecast:
            params["past_days"] = (today - start_date).days + 1
            params["forecast_days"] = 1
            url = RECENT_WEATHER_URL
        else:
            params["start_date"] = start_date.isoformat()
            params["end_date"] = end_date.isoformat()
            url = WEATHER_URL
        response = session.get(url, params=params, timeout=settings.weather_timeout)
        response.raise_for_status()
        body = response.json()
        hourly = body.get("hourly")
        if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
            raise ValueError(
                f"Open-Meteo returned an invalid hourly response for "
                f"{latitude}, {longitude}"
            )

        times = hourly["time"]
        temperatures = hourly.get("temperature_2m", [])
        precipitation = hourly.get("precipitation", [])
        surface_pressures = hourly.get("surface_pressure", [])
        relative_humidity = hourly.get("relative_humidity_2m", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        if not (
            len(times)
            == len(temperatures)
            == len(precipitation)
            == len(surface_pressures)
            == len(relative_humidity)
            == len(wind_speeds)
        ):
            raise ValueError(
                f"Open-Meteo returned mismatched hourly arrays for "
                f"{latitude}, {longitude}"
            )

        for index, timestamp in enumerate(times):
            hour = datetime.fromisoformat(timestamp)
            if hour.tzinfo is None:
                hour = hour.replace(tzinfo=WARSAW_TIMEZONE)
            else:
                hour = hour.astimezone(WARSAW_TIMEZONE)
            hour_bucket = hour.replace(minute=0, second=0, microsecond=0, tzinfo=None)
            weather_by_key[(latitude, longitude, hour_bucket)] = (
                temperatures[index],
                precipitation[index],
                surface_pressures[index],
                relative_humidity[index],
                wind_speeds[index],
            )

    keys = list(weather_by_key)
    return pa.table(
        {
            "lat_grid": pa.array([key[0] for key in keys], type=pa.float64()),
            "lon_grid": pa.array([key[1] for key in keys], type=pa.float64()),
            "hour_bucket": pa.array([key[2] for key in keys], type=pa.timestamp("us")),
            "temperature_2m": pa.array(
                [weather_by_key[key][0] for key in keys], type=pa.float64()
            ),
            "precipitation": pa.array(
                [weather_by_key[key][1] for key in keys], type=pa.float64()
            ),
            "surface_pressure_hpa": pa.array(
                [weather_by_key[key][2] for key in keys], type=pa.float64()
            ),
            "relative_humidity_2m": pa.array(
                [weather_by_key[key][3] for key in keys], type=pa.float64()
            ),
            "wind_speed_10m": pa.array(
                [weather_by_key[key][4] for key in keys], type=pa.float64()
            ),
        }
    )


def _gps_locations(bronze_files: list[str], settings: Settings) -> pa.Table:
    connection = create_duckdb_connection(settings)
    try:
        return connection.execute(
            """
            WITH gps AS (
                SELECT
                    ROUND(
                        TRY_CAST(
                            json_extract_string(data_json, '$.latitude') AS DOUBLE
                        ),
                        2
                    ) AS lat_grid,
                    ROUND(
                        TRY_CAST(
                            json_extract_string(data_json, '$.longitude') AS DOUBLE
                        ),
                        2
                    ) AS lon_grid,
                    CAST(
                        timezone(
                            'Europe/Warsaw',
                            to_timestamp(
                                TRY_CAST(
                                    json_extract_string(
                                        data_json, '$.recorded_at_epoch_s'
                                    ) AS DOUBLE
                                )
                            )
                        ) AS DATE
                    ) AS local_date
                FROM read_parquet(
                    $1,
                    filename = true,
                    union_by_name = true
                )
                WHERE stream = 'gps'
            )
            SELECT
                lat_grid,
                lon_grid,
                MIN(local_date) AS min_date,
                MAX(local_date) AS max_date
            FROM gps
            WHERE lat_grid IS NOT NULL
              AND lon_grid IS NOT NULL
              AND local_date IS NOT NULL
            GROUP BY lat_grid, lon_grid
            """,
            [bronze_files],
        ).to_arrow_table()
    finally:
        connection.close()


def enrich_weather_for_batch(bronze_files: list[str], settings: Settings) -> None:
    locations = _gps_locations(bronze_files, settings)
    session = create_weather_session(settings)
    try:
        weather = fetch_weather(locations, settings, session)
    finally:
        session.close()

    if weather.num_rows:
        LOGGER.info("Upserting %d hourly weather rows", weather.num_rows)
    merge_delta(weather, settings.weather_table, WEATHER_KEYS, [], settings)

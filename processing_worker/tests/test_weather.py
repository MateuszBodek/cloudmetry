from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pyarrow as pa
import requests

from processing_worker.src.weather import fetch_weather


def test_request_failure_skips_location_and_keeps_successful_weather(caplog) -> None:
    locations = pa.table(
        {
            "lat_grid": [51.1, 51.2],
            "lon_grid": [17.09, 17.1],
            "min_date": [date(2020, 1, 1), date(2020, 1, 1)],
            "max_date": [date(2020, 1, 1), date(2020, 1, 1)],
        }
    )
    response = Mock()
    response.json.return_value = {
        "hourly": {
            "time": ["2020-01-01T12:00"],
            "temperature_2m": [4.0],
            "precipitation": [0.0],
            "surface_pressure": [1000.0],
            "relative_humidity_2m": [80.0],
            "wind_speed_10m": [3.0],
        }
    }
    session = Mock()
    session.get.side_effect = [
        requests.exceptions.RetryError("Open-Meteo returned repeated 503s"),
        response,
    ]

    weather = fetch_weather(locations, SimpleNamespace(weather_timeout=20), session)

    assert weather.num_rows == 1  # noqa: S101
    assert weather.column("lat_grid").to_pylist() == [51.2]  # noqa: S101
    assert "continuing without weather" in caplog.text  # noqa: S101

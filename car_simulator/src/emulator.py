import csv
import json
import math
import re
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as mqtt

GPS_SAMPLE_PERIOD_SECONDS = 0.05
ACCELEROMETER_GROUP_SIZE = 5
CORE_TELEMETRY_COLUMNS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "core_telemetry_columns.txt"
)


class TelemetryEmulator:
    def __init__(self, csv_path):
        self.csv_path = Path(csv_path)
        data_dir = self.csv_path.parent
        self.gps_path = data_dir / "Location.csv"
        if not self.gps_path.exists():
            self.gps_path = data_dir / "gps.csv"
        self.accelerometer_path = data_dir / "Accelerometer.csv"
        if not self.accelerometer_path.exists():
            self.accelerometer_path = data_dir / "accelerometer.csv"
        self.is_running = False
        self._stop_event = threading.Event()
        self.vehicle_id = "test-01"
        self.drive_id = None
        self.topic_root = f"cloudmetry/vehicle/{self.vehicle_id}"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._playback_start: float | None = None
        self._sampled_at_start: datetime | None = None

    def start_engine(self):
        self.drive_id = str(uuid4())
        self.is_running = True
        self._stop_event.clear()
        self.client.connect("127.0.0.1", 1883, keepalive=60)
        self.client.loop_start()
        self._playback_start = time.monotonic()
        self._sampled_at_start = datetime.now(UTC)

        streams = (
            ("telemetry", self._read_telemetry_samples),
            ("gps", lambda: self._read_sensor_samples(self.gps_path, "gps")),
            (
                "accelerometer",
                lambda: self._read_sensor_samples(
                    self.accelerometer_path, "accelerometer"
                ),
            ),
        )
        errors = []

        def publish_stream(stream_name, read_samples):
            try:
                self._publish_stream(stream_name, read_samples())
            except Exception as error:
                errors.append(error)
                self._stop_event.set()

        workers = [
            threading.Thread(
                target=publish_stream,
                args=(stream_name, read_samples),
                name=f"telemetry-{stream_name}",
            )
            for stream_name, read_samples in streams
        ]

        try:
            for worker in workers:
                worker.start()
            while any(worker.is_alive() for worker in workers):
                for worker in workers:
                    worker.join(timeout=0.05)
            if errors:
                raise errors[0]
        finally:
            self.is_running = False
            self._stop_event.set()
            for worker in workers:
                if worker.ident is not None:
                    worker.join()
            self.client.loop_stop()
            self.client.disconnect()

    def _read_telemetry_samples(self):
        core_columns = [
            line.strip()
            for line in CORE_TELEMETRY_COLUMNS_PATH.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not core_columns:
            raise ValueError(
                f"No telemetry columns configured in {CORE_TELEMETRY_COLUMNS_PATH}"
            )
        if len(core_columns) != len(set(core_columns)):
            raise ValueError(
                f"Duplicate telemetry columns configured in "
                f"{CORE_TELEMETRY_COLUMNS_PATH}"
            )

        with self.csv_path.open(mode="r", encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, delimiter="\t")
            headers = next(reader, [])
            units = next(reader, [])
            if not headers:
                raise ValueError(f"Brak nagłówka w pliku {self.csv_path}")
            selected_columns = []
            missing_columns = []
            for column in core_columns:
                matches = [
                    index
                    for index, header in enumerate(headers)
                    if header.strip() == column
                ]
                if not matches:
                    missing_columns.append(column)
                    continue
                selected_index = next(
                    (
                        index
                        for index in matches
                        if index < len(units) and units[index].strip()
                    ),
                    matches[0],
                )
                selected_columns.append((column, selected_index))

            if missing_columns:
                raise ValueError(
                    f"Brak wymaganych kolumn w {self.csv_path}: "
                    f"{', '.join(missing_columns)}"
                )

            timestamp_index = next(
                index for column, index in selected_columns if column == "Time"
            )
            normalized_headers = []
            occurrences = {}
            for column, _ in selected_columns:
                camel_case_name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", column)
                name = re.sub(r"[^a-z0-9]+", "_", camel_case_name.lower()).strip("_")
                occurrences[name] = occurrences.get(name, 0) + 1
                if occurrences[name] > 1:
                    name = f"{name}_{occurrences[name]}"
                normalized_headers.append(name)

            previous_timestamp = None
            for row_number, values in enumerate(reader, start=3):
                if not values or not any(value.strip() for value in values):
                    continue

                if values[0] in {"s", "sec"} or values[0].startswith("MARK "):
                    continue

                try:
                    timestamp = float(values[timestamp_index])
                except (IndexError, ValueError) as error:
                    raise ValueError(
                        f"Nieprawidłowy znacznik czasu w wierszu {row_number}"
                    ) from error

                if not math.isfinite(timestamp):
                    raise ValueError(
                        f"Nieprawidłowy znacznik czasu w wierszu {row_number}"
                    )
                if previous_timestamp is not None and timestamp < previous_timestamp:
                    raise ValueError(
                        f"Znacznik czasu cofnął się w wierszu {row_number}"
                    )
                previous_timestamp = timestamp
                if len(values) != len(headers):
                    raise ValueError(
                        f"Nieprawidłowa liczba kolumn w wierszu {row_number}"
                    )
                yield (
                    timestamp,
                    {
                        normalized_headers[selected_position]: values[column_index]
                        for selected_position, (_, column_index) in enumerate(
                            selected_columns
                        )
                    },
                )

    def _read_sensor_samples(self, path, stream_name):
        with path.open(mode="r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            headers = reader.fieldnames or []
            timestamp_field = (
                "seconds_elapsed" if "seconds_elapsed" in headers else "time_s"
            )
            if stream_name == "gps":
                if {"latitude", "longitude", "heading_deg", "speed_kph"} <= set(
                    headers
                ):
                    fields = {
                        "latitude": ("latitude", 1.0),
                        "longitude": ("longitude", 1.0),
                        "heading_deg": ("heading_deg", 1.0),
                        "speed_kph": ("speed_kph", 1.0),
                    }
                else:
                    fields = {
                        "latitude": ("latitude", 1.0),
                        "longitude": ("longitude", 1.0),
                        "heading_deg": ("bearing", 1.0),
                        "speed_kph": ("speed", 3.6),
                    }
                if "time" in headers:
                    fields["recorded_at_epoch_s"] = ("time", 1e-9)
            elif stream_name == "accelerometer":
                if {"x_g", "y_g", "z_g"} <= set(headers):
                    fields = {
                        "x_g": ("x_g", 1.0),
                        "y_g": ("y_g", 1.0),
                        "z_g": ("z_g", 1.0),
                    }
                else:
                    fields = {
                        "x_g": ("x", 1 / 9.80665),
                        "y_g": ("y", 1 / 9.80665),
                        "z_g": ("z", 1 / 9.80665),
                    }
            else:
                raise ValueError(f"Nieznany strumień: {stream_name}")

            required_headers = {timestamp_field} | {
                source_field for source_field, _ in fields.values()
            }
            missing_headers = required_headers - set(headers)
            if missing_headers:
                raise ValueError(
                    f"Brak kolumn {sorted(missing_headers)} w pliku {path}"
                )

            def read_samples():
                previous_timestamp = None
                for row_number, sample in enumerate(reader, start=2):
                    try:
                        timestamp = float(sample[timestamp_field])
                        values = {
                            field: (
                                None
                                if field == "heading_deg"
                                and (
                                    sample[source_field] is None
                                    or not sample[source_field].strip()
                                )
                                else float(sample[source_field]) * scale
                            )
                            for field, (source_field, scale) in fields.items()
                        }
                    except (KeyError, TypeError, ValueError) as error:
                        raise ValueError(
                            f"Nieprawidłowa próbka w pliku {path}, wiersz {row_number}"
                        ) from error

                    if not math.isfinite(timestamp) or not all(
                        value is None or math.isfinite(value)
                        for value in values.values()
                    ):
                        raise ValueError(
                            f"Niefinitywna wartość w pliku {path}, wiersz {row_number}"
                        )
                    if (
                        previous_timestamp is not None
                        and timestamp < previous_timestamp
                    ):
                        raise ValueError(
                            f"Znacznik czasu cofnął się w pliku {path}, "
                            f"wiersz {row_number}"
                        )
                    previous_timestamp = timestamp
                    yield timestamp, values

            if stream_name == "gps":
                yield from self._resample_gps(read_samples())
            else:
                yield from self._average_accelerometer_samples(read_samples())

    def _average_accelerometer_samples(self, samples):
        batch = []

        for timestamp, values in samples:
            if any(value is None for value in values.values()):
                raise ValueError("Missing value in accelerometer sample")
            batch.append(
                (timestamp, {field: float(value) for field, value in values.items()})
            )
            if len(batch) == ACCELEROMETER_GROUP_SIZE:
                yield self._average_accelerometer_group(batch)
                batch = []

        if batch:
            yield self._average_accelerometer_group(batch)

    @staticmethod
    def _average_accelerometer_group(samples):
        count = len(samples)
        timestamp = sum(sample[0] for sample in samples) / count
        fields = samples[0][1]
        values = {
            field: sum(sample[1][field] for sample in samples) / count
            for field in fields
        }
        return timestamp, values

    def _resample_gps(self, samples):
        sample_iterator = iter(samples)
        previous = next(sample_iterator, None)
        if previous is None:
            return

        yield previous
        next_sample_time = previous[0] + GPS_SAMPLE_PERIOD_SECONDS

        for current in sample_iterator:
            previous_time, previous_values = previous
            current_time, current_values = current
            while next_sample_time < current_time:
                fraction = (next_sample_time - previous_time) / (
                    current_time - previous_time
                )
                yield (
                    next_sample_time,
                    self._interpolate_gps_values(
                        previous_values, current_values, fraction
                    ),
                )
                next_sample_time += GPS_SAMPLE_PERIOD_SECONDS

            if math.isclose(next_sample_time, current_time, rel_tol=0.0, abs_tol=1e-9):
                yield current
                next_sample_time += GPS_SAMPLE_PERIOD_SECONDS
            previous = current

    @staticmethod
    def _interpolate_gps_values(previous, current, fraction):
        values = {}
        for field, previous_value in previous.items():
            current_value = current[field]
            if previous_value is None or current_value is None:
                values[field] = None
            elif field == "heading_deg":
                heading_delta = (current_value - previous_value + 180) % 360 - 180
                values[field] = (previous_value + heading_delta * fraction) % 360
            else:
                values[field] = (
                    previous_value + (current_value - previous_value) * fraction
                )
        return values

    def _publish_stream(self, stream_name, samples):
        if self._playback_start is None or self._sampled_at_start is None:
            raise RuntimeError("Playback clock is not initialized")
        playback_start = self._playback_start
        sampled_at_start = self._sampled_at_start

        for timestamp, data in samples:
            if not self.is_running or self._stop_event.is_set():
                break

            deadline = playback_start + timestamp
            while self.is_running and not self._stop_event.is_set():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._stop_event.wait(min(remaining, 0.05))
            if not self.is_running or self._stop_event.is_set():
                break

            payload = {
                "vehicle_id": self.vehicle_id,
                "drive_id": self.drive_id,
                "stream": stream_name,
                "source_time_s": timestamp,
                "sampled_at": (
                    sampled_at_start + timedelta(seconds=timestamp)
                ).isoformat(),
                "generated_at": datetime.now(UTC).isoformat(),
                "data": data,
            }
            self._send_frame(stream_name, payload)

    def _send_frame(self, stream_name, data):
        message = json.dumps(data)
        result = self.client.publish(
            f"{self.topic_root}/{stream_name}",
            message,
            qos=1,
            retain=False,
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Nie udało się wysłać MQTT: {result.rc}")
        result.wait_for_publish(timeout=10)
        if not result.is_published():
            raise RuntimeError("Przekroczenie czasu wysyłania MQTT")

    def stop_engine(self):
        self.is_running = False
        self._stop_event.set()
        print("Emulacja zatrzymana")

import csv
import json
import math
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as mqtt


class TelemetryEmulator:
    def __init__(self, csv_path):
        self.csv_path = Path(csv_path)
        data_dir = self.csv_path.parent
        self.gps_path = data_dir / "gps.csv"
        self.accelerometer_path = data_dir / "accelerometer.csv"
        self.is_running = False
        self._stop_event = threading.Event()
        self.vehicle_id = "test-01"
        self.drive_id = None
        self.topic_root = f"cloudmetry/vehicle/{self.vehicle_id}"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def start_engine(self):
        self.drive_id = str(uuid4())
        self.is_running = True
        self._stop_event.clear()
        self.client.connect("127.0.0.1", 1883, keepalive=60)
        self.client.loop_start()

        streams = (
            ("telemetry", self._read_telemetry_samples),
            ("gps", lambda: self._read_sensor_samples(
                self.gps_path,
                ("latitude", "longitude", "heading_deg", "speed_kph"),
            )),
            ("accelerometer", lambda: self._read_sensor_samples(
                self.accelerometer_path,
                ("x_g", "y_g", "z_g"),
            )),
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
        with self.csv_path.open(mode="r", encoding="utf-8") as file:
            headers = file.readline().strip().replace('"', "").split("\t")
            try:
                timestamp_index = headers.index("time")
            except ValueError as error:
                raise ValueError("Brak kolumny time") from error

            previous_timestamp = None
            for row_number, line in enumerate(file, start=2):
                cleaned_line = line.strip().replace('"', "")
                if not cleaned_line:
                    continue

                values = cleaned_line.split("\t")
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
                yield timestamp, dict(zip(headers, values))

    def _read_sensor_samples(self, path, fields):
        with path.open(mode="r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            previous_timestamp = None
            for row_number, sample in enumerate(reader, start=2):
                try:
                    timestamp = float(sample["time_s"])
                    values = {field: float(sample[field]) for field in fields}
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(
                        f"Nieprawidłowa próbka w pliku {path}, wiersz {row_number}"
                    ) from error

                if not math.isfinite(timestamp) or not all(
                    math.isfinite(value) for value in values.values()
                ):
                    raise ValueError(
                        f"Niefinitywna wartość w pliku {path}, wiersz {row_number}"
                    )
                if previous_timestamp is not None and timestamp < previous_timestamp:
                    raise ValueError(
                        f"Znacznik czasu cofnął się w pliku {path}, "
                        f"wiersz {row_number}"
                    )
                previous_timestamp = timestamp
                yield timestamp, values

    def _publish_stream(self, stream_name, samples):
        first_timestamp = None
        playback_start = None
        sampled_at_start = None

        for timestamp, data in samples:
            if not self.is_running or self._stop_event.is_set():
                break

            if first_timestamp is None:
                first_timestamp = timestamp
                playback_start = time.monotonic()
                sampled_at_start = datetime.now(timezone.utc)
            else:
                deadline = playback_start + (timestamp - first_timestamp)
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
                    sampled_at_start
                    + timedelta(seconds=timestamp - first_timestamp)
                ).isoformat(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
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

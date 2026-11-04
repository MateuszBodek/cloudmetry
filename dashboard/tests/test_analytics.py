import unittest

from dashboard.analytics import (
    acceleration_record,
    acceleration_records,
    format_drive_duration,
)


class AccelerationRecordTests(unittest.TestCase):
    def test_acceleration_record_prefers_0_to_100(self) -> None:
        samples = [(float(time_s), float(time_s * 10)) for time_s in range(11)]

        self.assertEqual(acceleration_record(samples), ("0–100 km/h", 10.0))

    def test_acceleration_record_falls_back_to_0_to_60(self) -> None:
        samples = [(float(time_s), float(time_s * 8)) for time_s in range(11)]

        self.assertEqual(acceleration_record(samples), ("0–60 km/h", 7.5))

    def test_acceleration_record_falls_back_to_30_to_80(self) -> None:
        samples = [(float(time_s), float(30 + time_s * 5)) for time_s in range(11)]

        self.assertEqual(acceleration_record(samples), ("30–80 km/h", 10.0))

    def test_acceleration_record_does_not_bridge_telemetry_gaps(self) -> None:
        samples = [(0.0, 0.0), (1.0, 20.0), (5.0, 100.0)]

        self.assertIsNone(acceleration_record(samples))

    def test_acceleration_record_accepts_launch_speed_below_15_kmh(self) -> None:
        samples = [(0.0, 12.0), (1.0, 40.0), (2.0, 70.0), (3.0, 100.0)]

        self.assertEqual(acceleration_record(samples), ("0–100 km/h", 3.0))

    def test_acceleration_records_return_each_supported_interval(self) -> None:
        samples = [(float(speed // 10), float(speed)) for speed in range(0, 201, 10)]

        self.assertEqual(
            acceleration_records(samples),
            {
                "0–60 km/h": 6.0,
                "0–100 km/h": 10.0,
                "30–80 km/h": 5.0,
                "100–200 km/h": 10.0,
            },
        )


class DriveDurationFormatTests(unittest.TestCase):
    def test_seconds_are_displayed_as_seconds(self) -> None:
        self.assertEqual(format_drive_duration(45), "45 s")

    def test_minutes_are_displayed_as_minutes_and_seconds(self) -> None:
        self.assertEqual(format_drive_duration(125), "2 min 5 s")

    def test_long_drives_are_displayed_as_hours_and_minutes(self) -> None:
        self.assertEqual(format_drive_duration(3725), "1 h 2 min")

    def test_exact_hour_includes_both_units(self) -> None:
        self.assertEqual(format_drive_duration(3600), "1 h 0 min")

    def test_missing_duration_is_displayed_gracefully(self) -> None:
        self.assertEqual(format_drive_duration(None), "Brak danych")

from __future__ import annotations

import math
from collections.abc import Sequence


def _crossing_time(
    times: Sequence[float], speeds: Sequence[float], target_kmh: float
) -> float | None:
    if not speeds or speeds[0] > target_kmh:
        return None
    for index, speed in enumerate(speeds):
        if speed >= target_kmh:
            if index == 0:
                return times[index]
            previous_speed = speeds[index - 1]
            previous_time = times[index - 1]
            if speed == previous_speed:
                return times[index]
            fraction = (target_kmh - previous_speed) / (speed - previous_speed)
            return previous_time + fraction * (times[index] - previous_time)
    return None


def _segments(
    samples: Sequence[tuple[float, float]],
) -> list[tuple[list[float], list[float]]]:
    valid = [
        (time_s, speed_kmh)
        for time_s, speed_kmh in samples
        if math.isfinite(time_s) and math.isfinite(speed_kmh)
    ]
    valid.sort(key=lambda sample: sample[0])

    segments: list[tuple[list[float], list[float]]] = []
    times: list[float] = []
    speeds: list[float] = []
    peak_speed = -math.inf
    for time_s, speed_kmh in valid:
        if times and (time_s - times[-1] > 2.5 or speed_kmh < peak_speed - 8.0):
            segments.append((times, speeds))
            times, speeds = [], []
            peak_speed = -math.inf
        times.append(time_s)
        speeds.append(speed_kmh)
        peak_speed = max(peak_speed, speed_kmh)
    if times:
        segments.append((times, speeds))
    return segments


def acceleration_record(
    samples: Sequence[tuple[float, float]],
) -> tuple[str, float] | None:
    """Return the quickest continuous launch-to-speed record available."""
    records = acceleration_records(samples)
    for label in ("0–100 km/h", "0–60 km/h", "30–80 km/h"):
        if label in records:
            return label, records[label]
    return None


def acceleration_records(
    samples: Sequence[tuple[float, float]],
) -> dict[str, float]:
    """Return the quickest valid time for each supported speed interval."""
    segments = _segments(samples)
    records: dict[str, float] = {}
    for target_kmh, title in ((60.0, "0–60 km/h"), (100.0, "0–100 km/h")):
        interval_times: list[float] = []
        for times, speeds in segments:
            launch_indices = [
                index for index, speed in enumerate(speeds) if speed <= 5.0
            ]
            if not launch_indices:
                launch_indices = [
                    index for index, speed in enumerate(speeds) if speed < 15.0
                ]
            if launch_indices:
                start_index = launch_indices[0]
                finish_time = _crossing_time(
                    times[start_index:], speeds[start_index:], target_kmh
                )
                if finish_time is not None and finish_time >= times[start_index]:
                    interval_times.append(finish_time - times[start_index])
        if interval_times:
            records[title] = min(interval_times)

    for start_kmh, finish_kmh, title in (
        (30.0, 80.0, "30–80 km/h"),
        (100.0, 200.0, "100–200 km/h"),
    ):
        interval_times = []
        for times, speeds in segments:
            start_time = _crossing_time(times, speeds, start_kmh)
            finish_time = _crossing_time(times, speeds, finish_kmh)
            if (
                start_time is not None
                and finish_time is not None
                and finish_time > start_time
            ):
                interval_times.append(finish_time - start_time)
        if interval_times:
            records[title] = min(interval_times)
    return records


def format_drive_duration(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return "Brak danych"
    total_seconds = round(seconds)
    if total_seconds >= 3600:
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{hours} h {minutes} min"
    if total_seconds >= 60:
        minutes, remaining_seconds = divmod(total_seconds, 60)
        return f"{minutes} min {remaining_seconds} s"
    return f"{total_seconds} s"

from pathlib import Path

from common.src.logger import setup_logger
from src.emulator import TelemetryEmulator


def main() -> None:
    setup_logger("car_simulator")

    data_dir = Path(__file__).resolve().parents[1] / "data" / "2"
    csv_path = data_dir / "test_log_2.csv"
    emulator = TelemetryEmulator(csv_path=str(csv_path))

    try:
        emulator.start_engine()
    except KeyboardInterrupt:
        print("\nStop emulatora")
        emulator.stop_engine()


if __name__ == "__main__":
    main()

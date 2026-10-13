from pathlib import Path

from src.emulator import TelemetryEmulator
from common.src.logger import setup_logger


def main() -> None:
    setup_logger("car_simulator")

    csv_path = Path(__file__).resolve().parents[1] / "data" / "test_log.csv"
    emulator = TelemetryEmulator(csv_path=str(csv_path))

    try:
        emulator.start_engine()
    except KeyboardInterrupt:
        print("\nStop emulatora")
        emulator.stop_engine()

if __name__ == "__main__":
    main()

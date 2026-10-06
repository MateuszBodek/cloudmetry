from common.src.logger import setup_logger


def main() -> None:
    setup_logger("queue_worker")

if __name__ == "__main__":
    main()

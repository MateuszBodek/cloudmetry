import sys
from pathlib import Path
from typing import Any, Literal

from loguru import logger

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<magenta>{name}</magenta>:"
    "<cyan>{function}</cyan>:"
    "<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logger(
    service_name: str,
    log_dir: str = "logs",
    logs_format: str = LOG_FORMAT,
    json_output: bool = False,
    logs_level: LogLevel = "DEBUG",
    json_logs_level: LogLevel = "INFO",
) -> Any:
    logger.remove()

    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            format=logs_format,
            level=logs_level,
        )

    log_path: Path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    file_path: Path = log_path / f"{service_name}.log"

    logger.add(
        file_path,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        serialize=json_output,
        level=json_logs_level,
        enqueue=True,
    )

    logger.info("Logger configured for: {}", service_name)
    return logger

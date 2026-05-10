import logging
import os
from pathlib import Path

LOG_TO_FILE = os.getenv("LOG_TO_FILE", "false").lower() == "true"
LOGS_DIR = Path(os.getenv("LOGS_DIR", "/tmp/maslul_logs"))
LOGS_FORMAT = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"


class LoggerManager:
    logging_format = logging.Formatter(LOGS_FORMAT)

    def __init__(self, name: str = "maslul"):
        self.name = name
        self._init_logger()

    def _setup_file_handler(self, logger_instance: logging.Logger):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOGS_DIR / f"{self.name}.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.logging_format)
        logger_instance.addHandler(file_handler)

    def _init_logger(self):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(self.logging_format)

        logger_instance = logging.getLogger(self.name)
        logger_instance.setLevel(logging.DEBUG)
        logger_instance.handlers = []
        logger_instance.addHandler(stream_handler)

        if LOG_TO_FILE:
            self._setup_file_handler(logger_instance)

        self._logger = logger_instance

    def get_child(self, suffix: str) -> logging.Logger:
        return self._logger.getChild(suffix)

    @property
    def logger(self) -> logging.Logger:
        return self._logger


scraper_logger = LoggerManager("maslul.scrapers")

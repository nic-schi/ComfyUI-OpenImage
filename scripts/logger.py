# /scripts/logger.py

import logging
import sys
import copy
from .node_name import get_node_name
from enum import Enum


class LoggerSettings(Enum):
    LOG_LEVEL = logging.DEBUG
    LOG_NAME = "OpenImage"


class OpenImageLoggerFormatter(logging.Formatter):
    COLORS = {
        "INFO": "\033[0;32m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        record_copy = copy.copy(record)

        levelname = record_copy.levelname
        seq = self.COLORS.get(levelname, self.COLORS["RESET"])
        record_copy.levelname = f"{seq}{levelname}{self.COLORS['RESET']}"

        record_copy.name = f"\033[1;34m{record_copy.name}\033[0m"

        return super().format(record_copy)


def get_node_logger_prefix(extra_pnginfo, unique_id, display_name):
    return f"\"{get_node_name(extra_pnginfo, unique_id, display_name)}\"" + (f" ({display_name})" if display_name else "") + ":"


logger = logging.getLogger(LoggerSettings.LOG_NAME.value)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(OpenImageLoggerFormatter("[%(name)s][%(levelname)s] %(message)s"))
    logger.addHandler(handler)

logger.setLevel(LoggerSettings.LOG_LEVEL.value)

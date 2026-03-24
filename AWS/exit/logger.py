"""Logger for HRS exit AWS OpenSearch scripts."""
import json
import logging
from typing import Any, Dict


def setup_logger(name: str = "hrs_exit_opensearch", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


def log_json(logger, title: str, payload: Dict[str, Any]):
    logger.info(f"{title}:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

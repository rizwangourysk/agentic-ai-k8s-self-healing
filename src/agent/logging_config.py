import logging
from pathlib import Path


LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "agent.log"


logger = logging.getLogger("k8s-self-healing-agent")
logger.setLevel(logging.INFO)

# Prevent duplicate log messages if this module is imported more than once.
logger.propagate = False


if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)

    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

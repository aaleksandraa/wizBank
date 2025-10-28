import logging
from pathlib import Path

LOG_DIR = Path(Path.home() / ".wizvod" / "logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "worker.log"

def get_logger(name: str = "wizvod"):
    """Inicijalizuje globalni logger koji upisuje logove u ~/.wizvod/logs/worker.log"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger

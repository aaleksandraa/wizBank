from typing import Dict
from wizvod.core.db import Database

class AppConfig:
    def __init__(self, db: Database):
        self.db = db

    def get_settings(self) -> Dict[str, str]:
        return self.db.get_settings()

    def set(self, key: str, value: str):
        self.db.set_setting(key, value)

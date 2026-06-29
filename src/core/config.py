"""VAPT Tool - Configuration loader"""
import os
import yaml
from pathlib import Path
from src.exceptions import ConfigError


class Config:
    def __init__(self, config_path=None):
        if config_path is None:
            # Check local config.yaml first
            local_config = Path(__file__).parent.parent.parent / "vapt_config.yaml"
            if local_config.exists():
                config_path = str(local_config)
            else:
                config_path = os.environ.get("VAPT_CONFIG", "/opt/vapt-tool/config/config.yaml")
        self.config_path = config_path
        self._config = self._load()

    def _load(self):
        path = Path(self.config_path)
        if not path.exists():
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    def get(self, key, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def app_name(self):
        return self.get("app.name", "VAPT Tool")

    @property
    def db_url(self):
        return self.get("database.postgresql.url") or os.environ.get(
            "DATABASE_URL", "sqlite:///vapt_default.db"
        )

    @property
    def redis_url(self):
        return self.get("database.redis.url") or os.environ.get("REDIS_URL", "")

config = Config()

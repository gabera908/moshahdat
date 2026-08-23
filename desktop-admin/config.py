"""Desktop admin application configuration (stored in %APPDATA%)."""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

APP_NAME = "VideoPlatformAdmin"
APP_DIR = Path.home() / "AppData" / "Roaming" / APP_NAME if Path.home().joinpath("AppData").exists() else Path.home() / f".{APP_NAME}"
CONFIG_PATH = APP_DIR / "config.json"
LOG_DIR = APP_DIR / "logs"


@dataclass
class AppConfig:
    api_base_url: str = "http://localhost:6688/api/v1"
    language: str = "ar"
    theme: str = "dark"
    page_size: int = 25
    remember_username: bool = True
    saved_username: str = ""

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls) -> "AppConfig":
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            known = {f.name for f in cls.__dataclass_fields__.values()}
            return cls(**{k: v for k, v in data.items() if k in known})
        except (OSError, json.JSONDecodeError):
            return cls()

import json
from pathlib import Path

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS


RUNTIME_CONFIG_PATH = Path(BASE_DIR / "db" / "runtime_config.json")

DEFAULT_RUNTIME_CONFIG = {
    "localChromeHeadless": bool(LOCAL_CHROME_HEADLESS),
    "loginBrowserHeadless": False,
}


def _normalize_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def get_runtime_config() -> dict:
    config = DEFAULT_RUNTIME_CONFIG.copy()
    if RUNTIME_CONFIG_PATH.exists():
        try:
            raw = json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, default in DEFAULT_RUNTIME_CONFIG.items():
                    config[key] = _normalize_bool(raw.get(key), default)
        except Exception:
            pass
    return config


def save_runtime_config(config: dict) -> dict:
    normalized = DEFAULT_RUNTIME_CONFIG.copy()
    for key, default in DEFAULT_RUNTIME_CONFIG.items():
        normalized[key] = _normalize_bool(config.get(key), default)

    RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_CONFIG_PATH.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return normalized


def update_runtime_config(updates: dict) -> dict:
    current = get_runtime_config()
    for key in DEFAULT_RUNTIME_CONFIG:
        if key in updates:
            current[key] = _normalize_bool(updates.get(key), current[key])
    return save_runtime_config(current)


def get_local_chrome_headless() -> bool:
    return get_runtime_config()["localChromeHeadless"]


def get_login_browser_headless() -> bool:
    return get_runtime_config()["loginBrowserHeadless"]

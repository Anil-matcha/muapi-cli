"""Config management — stores API key in OS keychain, with ~/.muapi/config.json fallback."""
import json
import os
from pathlib import Path
from typing import Optional

_CONFIG_DIR = Path.home() / ".muapi"
_CONFIG_FILE = _CONFIG_DIR / "config.json"
_KEYRING_SERVICE = "muapi-cli"
_KEYRING_USER = "api-key"

BASE_URL = os.environ.get("MUAPI_BASE_URL", "https://api.muapi.ai/api/v1")


def _try_keyring() -> tuple[bool, Optional[str]]:
    try:
        import keyring
        val = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER)
        return True, val
    except Exception:
        return False, None


def get_api_key() -> Optional[str]:
    # 1. Environment variable always wins
    if key := os.environ.get("MUAPI_API_KEY"):
        return key
    # 2. OS keychain
    ok, val = _try_keyring()
    if ok and val:
        return val
    # 3. Config file fallback
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text())
            return data.get("api_key")
        except Exception:
            pass
    return None


def save_api_key(api_key: str) -> str:
    """Save API key; returns where it was saved ('keychain' or 'file')."""
    ok, _ = _try_keyring()
    if ok:
        import keyring
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER, api_key)
        return "keychain"
    # Fallback: write to file
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if _CONFIG_FILE.exists():
        try:
            existing = json.loads(_CONFIG_FILE.read_text())
        except Exception:
            pass
    existing["api_key"] = api_key
    _CONFIG_FILE.write_text(json.dumps(existing, indent=2))
    _CONFIG_FILE.chmod(0o600)
    return "file"


def get_setting(key: str) -> Optional[str]:
    """Read a value from the settings section of the config file."""
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text())
            return data.get("settings", {}).get(key)
        except Exception:
            pass
    return None


def set_setting(key: str, value: str) -> None:
    """Write a value to the settings section of the config file."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if _CONFIG_FILE.exists():
        try:
            existing = json.loads(_CONFIG_FILE.read_text())
        except Exception:
            pass
    existing.setdefault("settings", {})[key] = value
    _CONFIG_FILE.write_text(json.dumps(existing, indent=2))
    _CONFIG_FILE.chmod(0o600)


def get_all_settings() -> dict:
    """Return all settings as a dict."""
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text())
            return data.get("settings", {})
        except Exception:
            pass
    return {}


def get_key_info() -> tuple[Optional[str], str]:
    """Return (api_key, source_description) for display in status/whoami."""
    if key := os.environ.get("MUAPI_API_KEY"):
        return key, "env:MUAPI_API_KEY"
    ok, val = _try_keyring()
    if ok and val:
        return val, "keychain"
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text())
            if key := data.get("api_key"):
                return key, f"file:{_CONFIG_FILE}"
        except Exception:
            pass
    return None, "not set"


def delete_api_key() -> None:
    ok, _ = _try_keyring()
    if ok:
        try:
            import keyring
            keyring.delete_password(_KEYRING_SERVICE, _KEYRING_USER)
        except Exception:
            pass
    if _CONFIG_FILE.exists():
        data = json.loads(_CONFIG_FILE.read_text())
        data.pop("api_key", None)
        _CONFIG_FILE.write_text(json.dumps(data, indent=2))

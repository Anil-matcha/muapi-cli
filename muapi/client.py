"""Async HTTP client wrapping the muapi submit → poll pattern."""
import time
from typing import Any, Optional

import httpx

from .config import BASE_URL, get_api_key

_DEFAULT_TIMEOUT = 30.0
_POLL_INTERVAL = 3        # seconds between polls
_MAX_POLL_SECONDS = 600   # 10 minutes


class MuapiError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code

    @property
    def exit_code(self) -> int:
        """Map HTTP status codes to semantic CLI exit codes."""
        from .exitcodes import AUTH_ERROR, RATE_LIMITED, BILLING_ERROR, NOT_FOUND, ERROR
        return {
            401: AUTH_ERROR,
            403: AUTH_ERROR,
            404: NOT_FOUND,
            429: RATE_LIMITED,
            402: BILLING_ERROR,
        }.get(self.status_code, ERROR)


def _headers(api_key: str) -> dict:
    return {"x-api-key": api_key, "Content-Type": "application/json"}


def _get_key() -> str:
    key = get_api_key()
    if not key:
        raise MuapiError(
            "No API key configured. Run: muapi auth configure"
        )
    return key


# ── Low-level calls ────────────────────────────────────────────────────────────

def post(endpoint: str, payload: dict) -> dict:
    """Submit a generation request; returns raw response dict."""
    key = _get_key()
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
        resp = client.post(url, json=payload, headers=_headers(key))
    if resp.status_code >= 400:
        raise MuapiError(resp.text, resp.status_code)
    return resp.json()


def get_result(request_id: str) -> dict:
    """Fetch a single prediction result (no polling)."""
    key = _get_key()
    url = f"{BASE_URL}/predictions/{request_id}/result"
    with httpx.Client(timeout=_DEFAULT_TIMEOUT) as client:
        resp = client.get(url, headers=_headers(key))
    if resp.status_code >= 400:
        raise MuapiError(resp.text, resp.status_code)
    return resp.json()


def upload_file(file_path: str) -> dict:
    """Upload a local file, returns the upload response (url, etc.)."""
    key = _get_key()
    url = f"{BASE_URL}/upload_file"
    with open(file_path, "rb") as f:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                url,
                files={"file": (file_path.split("/")[-1], f)},
                headers={"x-api-key": key},
            )
    if resp.status_code >= 400:
        raise MuapiError(resp.text, resp.status_code)
    return resp.json()


# ── Polling ────────────────────────────────────────────────────────────────────

def wait_for_result(
    request_id: str,
    poll_interval: int = _POLL_INTERVAL,
    max_seconds: int = _MAX_POLL_SECONDS,
    progress_callback=None,
) -> dict:
    """Poll until status is 'completed' or 'failed'."""
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        result = get_result(request_id)
        status = result.get("status", "")
        if progress_callback:
            progress_callback(status)
        if status == "completed":
            return result
        if status == "failed":
            raise MuapiError(f"Generation failed: {result.get('error', 'unknown error')}")
        time.sleep(poll_interval)
    raise MuapiError(f"Timed out waiting for result after {max_seconds}s")


# ── Convenience: submit + optional wait ───────────────────────────────────────

def generate(
    endpoint: str,
    payload: dict,
    wait: bool = True,
    poll_interval: int = _POLL_INTERVAL,
    progress_callback=None,
) -> dict:
    result = post(endpoint, payload)
    request_id = result.get("request_id") or result.get("id")
    if not wait or not request_id:
        return result
    return wait_for_result(request_id, poll_interval, progress_callback=progress_callback)

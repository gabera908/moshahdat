"""Async API client for the FastAPI backend.

Uses QThread workers so the UI never blocks. Handles:
- login/refresh token lifecycle
- friendly Arabic errors
- offline detection
"""
import json
import threading
import time
from typing import Any, Callable

import httpx
from PySide6.QtCore import QObject, QThread, Signal

from config import AppConfig
from utils.logging_setup import ApiStatusError, log


class ApiClient:
    """Thread-safe HTTP client shared by all worker threads."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._lock = threading.Lock()
        self.on_session_expired: Callable[[], None] | None = None

    # ------------------------------------------------ tokens
    def set_tokens(self, access: str, refresh: str) -> None:
        with self._lock:
            self._access_token = access
            self._refresh_token = refresh

    def clear_tokens(self) -> None:
        self.set_tokens("", "")

    @property
    def has_tokens(self) -> bool:
        return bool(self._access_token)

    def base_url(self) -> str:
        return self.config.api_base_url.rstrip("/")

    def set_base_url(self, url: str) -> None:
        self.config.api_base_url = url.rstrip("/")
        self.config.save()

    # ------------------------------------------------ low level
    def _headers(self, auth: bool = True) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _request_sync(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        data: dict | None = None,
        auth: bool = True,
        _retry_auth: bool = True,
    ) -> Any:
        url = f"{self.base_url()}{path}"
        headers = self._headers(auth)
        if data is not None:
            # Form payload (login): let httpx set application/x-www-form-urlencoded
            headers.pop("Content-Type", None)
        try:
            resp = httpx.request(
                method,
                url,
                json=json_body if data is None else None,
                data=data,
                headers=headers,
                timeout=15.0,
            )
        except (httpx.ConnectError, httpx.TimeoutException):
            raise

        if resp.status_code == 401 and auth and _retry_auth and self._refresh_token:
            if self._try_refresh():
                return self._request_sync(
                    method, path, json_body=json_body, data=data, auth=auth, _retry_auth=False
                )
            raise ApiStatusError("انتهت صلاحية الجلسة، يرجى تسجيل الدخول مجددًا", 401)

        try:
            body = resp.json()
        except json.JSONDecodeError:
            body = {}

        if not resp.is_success:
            message = body.get("message") or body.get("detail") or f"خطأ من الخادم ({resp.status_code})"
            code = body.get("error_code") or ""
            log.warning("API %s %s -> %s %s", method, path, resp.status_code, code)
            raise ApiStatusError(message, resp.status_code, code)

        return body.get("data", body)

    def _try_refresh(self) -> bool:
        if not self._refresh_token:
            return False
        try:
            resp = httpx.post(
                f"{self.base_url()}/auth/refresh",
                json={"refresh_token": self._refresh_token},
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                self.set_tokens(data["access_token"], data["refresh_token"])
                return True
        except (httpx.HTTPError, KeyError, json.JSONDecodeError):
            pass
        self.clear_tokens()
        if self.on_session_expired:
            self.on_session_expired()
        return False

    # ------------------------------------------------ public API calls
    def login(self, username: str, password: str) -> dict:
        body = self._request_sync(
            "POST",
            "/auth/login",
            data={"username": username, "password": password},
            auth=False,
        )
        self.set_tokens(body["access_token"], body["refresh_token"])
        return body

    def logout(self) -> None:
        self.clear_tokens()

    def get(self, path: str, **kwargs) -> Any:
        return self._request_sync("GET", path, **kwargs)

    def post(self, path: str, json_body: Any = None, **kwargs) -> Any:
        return self._request_sync("POST", path, json_body=json_body, **kwargs)

    def put(self, path: str, json_body: Any = None) -> Any:
        return self._request_sync("PUT", path, json_body=json_body)

    def delete(self, path: str) -> Any:
        return self._request_sync("DELETE", path)

    # Raw variants keep the whole envelope {success, message, data}.
    def post_raw(self, path: str, json_body: Any = None, **kwargs) -> Any:
        return self._raw("POST", path, json_body=json_body, **kwargs)

    def get_raw(self, path: str) -> Any:
        return self._raw("GET", path)

    def health_check(self) -> dict:
        """Ping the backend root health endpoint."""
        base_root = self.base_url().removesuffix("/api/v1")
        resp = httpx.get(f"{base_root}/healthz", timeout=8.0)
        resp.raise_for_status()
        return resp.json()

    def _raw(self, method: str, path: str, **kw) -> Any:
        url = f"{self.base_url()}{path}"
        resp = httpx.request(
            method, url,
            json=kw.get("json_body"),
            headers=self._headers(kw.get("auth", True)),
            timeout=15.0,
        )
        try:
            body = resp.json()
        except json.JSONDecodeError:
            body = {}
        if not resp.is_success:
            raise ApiStatusError(
                body.get("message") or f"خطأ من الخادم ({resp.status_code})",
                resp.status_code,
                body.get("error_code", ""),
            )
        return body


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    offline = Signal()


class ApiWorker(QThread):
    """Runs an API call off the GUI thread; emits finished/failed/offline."""

    def __init__(
        self,
        client: ApiClient,
        fn_name: str,
        args: tuple = (),
        kwargs: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.signals = WorkerSignals()
        self.client = client
        self.fn_name = fn_name
        self.args = args
        self.kwargs = kwargs or {}

    def run(self):  # noqa: D102
        try:
            fn: Callable = getattr(self.client, self.fn_name)
            result = fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            from utils.logging_setup import log

            log.warning("offline: %s", exc)
            self.signals.offline.emit()
            self.signals.failed.emit(
                "لا يوجد اتصال بالخادم.\nيرجى التحقق من اتصال الإنترنت."
            )
        except ApiStatusError as exc:
            self.signals.failed.emit(exc.user_message)
        except Exception as exc:  # noqa: BLE001
            log.exception("worker failed: %s", self.fn_name)
            self.signals.failed.emit(f"حدث خطأ غير متوقع: {exc}")


def start_worker(client, fn_name, on_done, on_fail, args=(), kwargs=None, on_offline=None):
    """Convenience helper: launch a worker wired to callbacks."""
    worker = ApiWorker(client, fn_name, args=args, kwargs=kwargs)

    def done(result):
        on_done(result)
        worker.deleteLater()

    def fail(msg):
        on_fail(msg)
        worker.deleteLater()

    worker.signals.finished.connect(done)
    worker.signals.failed.connect(fail)
    if on_offline:
        worker.signals.offline.connect(on_offline)
    worker.start()
    return worker

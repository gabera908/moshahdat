"""File logging with friendly Arabic user-facing error mapping (plan §32)."""
import logging
import logging.handlers
from pathlib import Path

from config import LOG_DIR


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("vpadmin")
    if logger.handlers:
        return logger
    handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


log = setup_logging()


def friendly_error(exc: Exception) -> str:
    """Map technical exceptions to clear Arabic messages."""
    import httpx

    if isinstance(exc, httpx.ConnectError):
        return "لا يوجد اتصال بالخادم.\nيرجى التحقق من اتصال الإنترنت وإعدادات الخادم."
    if isinstance(exc, httpx.TimeoutException):
        return "انتهت مهلة الاتصال بالخادم.\nحاول مرة أخرى."
    if isinstance(exc, ApiStatusError):
        return exc.user_message
    log.exception("unexpected error")
    return "حدث خطأ غير متوقع.\nراجع ملف السجل لمزيد من التفاصيل."


class ApiStatusError(Exception):
    """API returned an error status with a user-facing message."""

    def __init__(self, message: str, status_code: int, error_code: str = ""):
        super().__init__(message)
        self.user_message = message or "تعذر تنفيذ العملية"
        self.status_code = status_code
        self.error_code = error_code

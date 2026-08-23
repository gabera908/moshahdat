"""Settings view: server URL + connection test."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient, start_worker
from config import AppConfig
from widgets.common import OfflineBanner, show_toast


class SettingsView(QWidget):
    def __init__(self, client: ApiClient, config: AppConfig):
        super().__init__()
        self.client = client
        self.config = config

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        self.banner = OfflineBanner()
        root.addWidget(self.banner)

        title = QLabel("إعدادات الاتصال")
        title.setStyleSheet("font-weight: 800; font-size: 15px;")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        self.url_input = QLineEdit(config.api_base_url)
        self.url_input.setMinimumWidth(380)
        form.addRow("عنوان الخادم (API):", self.url_input)

        row = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        test_btn = QPushButton("اختبار الاتصال")
        test_btn.clicked.connect(self._test)
        row.addWidget(save_btn)
        row.addWidget(test_btn)
        row.addStretch()

        root.addLayout(form)
        root.addLayout(row)
        root.addStretch()

        hint = QLabel(
            "ملاحظة: يجب أن يكون عنوان الخادم متاحًا من هذا الجهاز.\n"
            "مثال محلي: http://localhost:8080/api/v1 — مثال خادم: https://example.com/api/v1"
        )
        hint.setObjectName("HintText")
        hint.setWordWrap(True)
        root.addWidget(hint)

    def on_show(self) -> None:
        self.url_input.setText(self.client.config.api_base_url)

    def refresh(self) -> None:
        pass

    def _save(self) -> None:
        url = self.url_input.text().strip().rstrip("/")
        if not url:
            return
        self.client.set_base_url(url)
        show_toast(self.window(), "تم حفظ الإعدادات", "success")

    def _test(self) -> None:
        url = self.url_input.text().strip().rstrip("/")
        if url != self.client.base_url():
            self.client.set_base_url(url)
        start_worker(
            self.client, "health_check",
            on_done=lambda d: show_toast(self.window(), "الاتصال ناجح ✓", "success"),
            on_fail=lambda m: show_toast(self.window(), "تعذر الاتصال بالخادم ✗", "error"),
        )

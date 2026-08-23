"""Audit log browser (admin)."""
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient, start_worker
from config import AppConfig
from widgets.common import OfflineBanner

ACTION_LABELS = {
    "create": "إنشاء",
    "update": "تعديل",
    "delete": "حذف",
    "publish": "نشر",
    "unpublish": "إلغاء نشر",
    "archive": "أرشفة",
    "duplicate": "نسخ",
    "login": "دخول",
    "logout": "خروج",
}

ENTITY_LABELS = {
    "video": "فيديو",
    "category": "تصنيف",
    "tag": "وسم",
    "playlist": "قائمة",
    "user": "مستخدم",
}


class LogsView(QWidget):
    def __init__(self, client: ApiClient, config: AppConfig):
        super().__init__()
        self.client = client
        self.config = config

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        self.banner = OfflineBanner()
        root.addWidget(self.banner)

        bar = QHBoxLayout()
        bar.addStretch()
        reload_btn = QPushButton("تحديث")
        reload_btn.clicked.connect(self.refresh)
        bar.addWidget(reload_btn)
        root.addLayout(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["الوقت", "المستخدم", "الإجراء", "العنصر", "التفاصيل"])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        root.addWidget(self.table, 1)

    def on_show(self) -> None:
        self.load()

    def refresh(self) -> None:
        self.load()

    def load(self) -> None:
        self.banner.hide()
        start_worker(
            self.client, "get",
            on_done=self._apply_rows, on_fail=lambda m: None,
            args=("/audit-logs?page_size=100",), kwargs={"auth": True},
            on_offline=lambda: self.banner.show(),
        )

    def _apply_rows(self, data) -> None:
        items = data.get("items", [])
        self.table.setRowCount(0)
        for entry in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            created = (entry.get("created_at") or "").replace("T", " ")[:19]
            self.table.setItem(row, 0, QTableWidgetItem(created))
            username = entry.get("username") or f"#{entry.get('user_id')}" or "—"
            self.table.setItem(row, 1, QTableWidgetItem(username or "النظام"))
            action_item = QTableWidgetItem(ACTION_LABELS.get(entry["action"], entry["action"]))
            self.table.setItem(row, 2, action_item)
            entity = ENTITY_LABELS.get(entry["entity_type"], entry["entity_type"])
            entity_id = entry.get("entity_id")
            entity_text = f"{entity} {entity_id if entity_id else ''}".strip()
            self.table.setItem(row, 3, QTableWidgetItem(entity_text))

            details = entry.get("details")
            details_text = ""
            if isinstance(details, dict):
                parts = [f"{k}: {v}" for k, v in list(details.items())[:3]]
                details_text = ", ".join(parts)
            self.table.setItem(row, 4, QTableWidgetItem(details_text))

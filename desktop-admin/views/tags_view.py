"""Tags management: search, create, rename, delete."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient, start_worker
from config import AppConfig
from widgets.common import OfflineBanner, show_toast


class TagsView(QWidget):
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
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 ابحث في الوسوم...")
        self.search_box.returnPressed.connect(lambda: self.load(page=1))
        bar.addWidget(self.search_box, 1)
        add_btn = QPushButton("+ وسم جديد")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add)
        bar.addWidget(add_btn)
        reload = QPushButton("تحديث")
        reload.clicked.connect(self.refresh)
        bar.addWidget(reload)
        root.addLayout(bar)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["الوسم", "المعرّف", ""])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        self.page = 1

    def on_show(self) -> None:
        self.load()

    def refresh(self) -> None:
        self.load()

    def load(self, page: int | None = None) -> None:
        if page:
            self.page = page
        from urllib.parse import quote

        q = quote(self.search_box.text().strip())
        suffix = f"?q={q}&page={self.page}&page_size=50" if q else f"?page={self.page}&page_size=50"
        start_worker(
            self.client, "get",
            on_done=self._apply_rows, on_fail=self._fail,
            args=(f"/tags{suffix}",),
        )

    def _apply_rows(self, data) -> None:
        items = data.get("items", [])
        meta = data.get("meta", {})
        self.total_pages = max(1, meta.get("pages", 1))
        self.table.setRowCount(0)
        for t in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name_item = QTableWidgetItem(t["name"])
            name_item.setData(Qt.UserRole, t["id"])
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(t["slug"]))

            actions = QWidget()
            lay = QHBoxLayout(actions)
            lay.setContentsMargins(4, 2, 4, 2)
            edit_b = QPushButton("تعديل")
            del_b = QPushButton("حذف")
            del_b.setObjectName("Danger")
            tid = t["id"]
            name = t["name"]
            edit_b.clicked.connect(lambda _, n=name, i=tid: self._rename(n, i))
            del_b.clicked.connect(lambda _, i=tid: self._delete(i))
            for b in (edit_b, del_b):
                b.setFixedHeight(26)
                lay.addWidget(b)
            actions.setLayout(lay)
            self.table.setCellWidget(row, 2, actions)

    def _add(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "وسم جديد", "اسم الوسم:")
        if not ok or not name.strip():
            return
        start_worker(
            self.client, "post",
            on_done=lambda d: (show_toast(self.window(), "تم إضافة الوسم", "success"), self.refresh()),
            on_fail=self._fail,
            args=("/tags",), kwargs={"json_body": {"name": name.strip()}},
        )

    def _rename(self, current: str, tid: int) -> None:
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "تعديل الوسم", "الاسم:", text=current)
        if not ok or not name.strip():
            return
        start_worker(
            self.client, "put",
            on_done=lambda d: (show_toast(self.window(), "تم التحديث", "success"), self.refresh()),
            on_fail=self._fail,
            args=(f"/tags/{tid}",), kwargs={"json_body": {"name": name.strip()}},
        )

    def _delete(self, tid: int) -> None:
        confirm = QMessageBox.question(
            self, "تأكيد الحذف", "حذف هذا الوسم؟ سيُزال من كل الفيديوهات المرتبطة به.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        start_worker(
            self.client, "delete",
            on_done=lambda d: (show_toast(self.window(), "تم الحذف", "success"), self.refresh()),
            on_fail=self._fail,
            args=(f"/tags/{tid}",),
        )

    def _fail(self, message: str) -> None:
        show_toast(self.window(), message, "error")

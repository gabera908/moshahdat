"""Categories management with reorder buttons."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
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


class CategoriesView(QWidget):
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
        add_btn = QPushButton("+ تصنيف جديد")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add)
        bar.addWidget(add_btn)
        bar.addStretch()
        up = QPushButton("▲ أعلى")
        down = QPushButton("▼ أسفل")
        up.clicked.connect(lambda: self._move(-1))
        down.clicked.connect(lambda: self._move(1))
        bar.addWidget(up)
        bar.addWidget(down)
        reload = QPushButton("تحديث")
        reload.clicked.connect(self.refresh)
        bar.addWidget(reload)
        root.addLayout(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["الاسم", "المعرّف", "الوصف", "عدد الفيديوهات", ""])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        root.addWidget(self.table, 1)

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.load(include_inactive=True)

    def refresh(self) -> None:
        self.load(include_inactive=True)

    def load(self, include_inactive: bool = False) -> None:
        self.banner.hide()
        suffix = "?include_inactive=true" if include_inactive else ""
        start_worker(
            self.client, "get",
            on_done=self._apply_rows, on_fail=self._fail,
            args=(f"/categories{suffix}",), kwargs={"auth": True},
            on_offline=lambda: self.banner.show(),
        )

    def _apply_rows(self, data) -> None:
        items = data.get("items", [])
        self._items = items
        self.table.setRowCount(0)
        for c in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name_item = QTableWidgetItem(c["name"])
            name_item.setData(Qt.UserRole, c["id"])
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(c["slug"]))
            self.table.setItem(row, 2, QTableWidgetItem(c.get("description") or ""))
            count = QTableWidgetItem(str(c.get("videos_count", 0)))
            count.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, count)

            actions = QWidget()
            lay = QHBoxLayout(actions)
            lay.setContentsMargins(4, 2, 4, 2)
            edit_btn = QPushButton("تعديل")
            del_btn = QPushButton("حذف")
            del_btn.setObjectName("Danger")
            cid = c["id"]
            edit_btn.clicked.connect(lambda _, i=cid: self._edit(i))
            del_btn.clicked.connect(lambda _, i=cid: self._delete(i))
            for b in (edit_btn, del_btn):
                b.setFixedHeight(26)
                lay.addWidget(b)

            self.table.setCellWidget(row, 4, actions)


    def _pick_parent(self, exclude_id=None):
        """Ask for an optional parent from existing categories."""
        items = getattr(self, "_items", [])
        options = ["— بدون أب —"]
        ids = [None]
        for c in items:
            if exclude_id is not None and c["id"] == exclude_id:
                continue
            label = f"{c['name']}  ({c['slug']})"
            options.append(label)
            ids.append(c["id"])
        choice, ok = QInputDialog.getItem(self, "التصنيف الأب", "ضع التصنيف تحت:", options, 0, False)
        if not ok:
            return False, None
        return True, ids[options.index(choice)]

    def _current_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _add(self) -> None:
        name, ok = QInputDialog.getText(self, "تصنيف جديد", "اسم التصنيف:")
        if not ok or not name.strip():
            return
        ok_p, parent_id = self._pick_parent()
        if not ok_p:
            return
        payload = {"name": name.strip()}
        if parent_id is not None:
            payload["parent_id"] = parent_id
        start_worker(
            self.client, "post",
            on_done=lambda d: (show_toast(self.window(), "تم إنشاء التصنيف", "success"), self.refresh()),
            on_fail=self._fail,
            args=("/categories",), kwargs={"json_body": payload},
        )

    def _edit(self, cid: int) -> None:
        cat = next((c for c in getattr(self, "_items", []) if c["id"] == cid), None)
        if not cat:
            return
        name, ok = QInputDialog.getText(self, "تعديل التصنيف", "الاسم:", text=cat["name"])
        if not ok or not name.strip():
            return
        desc = cat.get("description") or ""
        desc, ok2 = QInputDialog.getMultiLineText(self, "الوصف", "الوصف:", desc)
        ok_p, parent_id = self._pick_parent(exclude_id=cid)
        if not ok_p:
            return
        payload = {
            "name": name.strip(),
            "description": (desc.strip() if ok2 and desc.strip() else None),
            "parent_id": parent_id,
        }
        start_worker(
            self.client, "put",
            on_done=lambda d: (show_toast(self.window(), "تم التحديث", "success"), self.refresh()),
            on_fail=self._fail,
            args=(f"/categories/{cid}",), kwargs={"json_body": payload},
        )

    def _delete(self, cid: int) -> None:
        confirm = QMessageBox.question(
            self, "تأكيد الحذف",
            "هل أنت متأكد من حذف هذا التصنيف؟\nهذا الإجراء لا يمكن التراجع عنه.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        start_worker(
            self.client, "delete",
            on_done=lambda d: (show_toast(self.window(), "تم الحذف", "success"), self.refresh()),
            on_fail=self._fail,
            args=(f"/categories/{cid}",),
        )

    def _move(self, delta: int) -> None:
        """Swap selected category with neighbor then push new order."""
        row = self.table.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= self.table.rowCount():
            return

        ids = [self.table.item(r, 0).data(Qt.UserRole) for r in range(self.table.rowCount())]
        ids[row], ids[target] = ids[target], ids[row]
        start_worker(
            self.client, "put",
            on_done=lambda d: self.refresh(),
            on_fail=self._fail,
            args=("/categories/reorder/all",), kwargs={"json_body": {"ids": ids}},
        )

    def _fail(self, message: str) -> None:
        show_toast(self.window(), message, "error")

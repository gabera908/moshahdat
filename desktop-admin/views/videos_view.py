"""Videos management: searchable, filterable table + bulk actions + CRUD."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient, start_worker
from config import AppConfig
from utils.logging_setup import log
from views.video_editor_dialog import VideoEditorDialog
from widgets.common import OfflineBanner, show_toast

STATUS_LABELS = {
    "draft": "مسودة",
    "pending": "بالانتظار",
    "published": "منشور",
    "archived": "مؤرشف",
}
SOURCE_LABELS = {
    "youtube": "YouTube",
    "gdrive": "Google Drive",
    "vimeo": "Vimeo",
    "dropbox": "Dropbox",
    "direct": "مباشر",
    "embed": "Embed",
}


class VideosView(QWidget):
    def __init__(self, client: ApiClient, config: AppConfig):
        super().__init__()
        self.client = client
        self.config = config

        self.page = 1
        self.pages = 1
        self.total = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        self.banner = OfflineBanner()
        root.addWidget(self.banner)

        # ---- toolbar row 1: search + filters
        filters = QHBoxLayout()
        filters.setSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 ابحث بالعنوان أو الوصف... (Ctrl+F)")
        self.search_box.returnPressed.connect(lambda: self.load(page=1))
        filters.addWidget(self.search_box, 3)

        self.status_filter = QComboBox()
        self.status_filter.addItem("كل الحالات", "")
        for value, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, value)
        self.status_filter.currentIndexChanged.connect(lambda *_: self.load(page=1))
        filters.addWidget(self.status_filter, 1)

        self.sort_select = QComboBox()
        for value, label in [
            ("newest", "الأحدث"),
            ("views", "الأكثر مشاهدة"),
            ("oldest", "الأقدم"),
            ("title", "أبجديًا"),
        ]:
            self.sort_select.addItem(label, value)
        self.sort_select.currentIndexChanged.connect(lambda *_: self.load(page=1))
        filters.addWidget(self.sort_select, 1)

        reload_btn = QPushButton("تحديث")
        reload_btn.clicked.connect(self.refresh)
        filters.addWidget(reload_btn)
        root.addLayout(filters)

        # ---- toolbar row 2: actions
        actions = QHBoxLayout()

        add_btn = QPushButton("+ إضافة فيديو")
        add_btn.setObjectName("Primary")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_video)
        actions.addWidget(add_btn)

        self.bulk_publish = QPushButton("نشر المحدد")
        self.bulk_publish.clicked.connect(lambda: self._bulk("publish"))
        self.bulk_unpublish = QPushButton("إلغاء النشر")
        self.bulk_unpublish.clicked.connect(lambda: self._bulk("unpublish"))
        self.bulk_archive = QPushButton("أرشفة المحدد")
        self.bulk_archive.clicked.connect(lambda: self._bulk("archive"))
        self.bulk_delete = QPushButton("حذف المحدد")
        self.bulk_delete.setObjectName("Danger")
        self.bulk_delete.clicked.connect(lambda: self._bulk("delete"))

        for b in (self.bulk_publish, self.bulk_unpublish, self.bulk_archive, self.bulk_delete):
            actions.addWidget(b)
        actions.addStretch()

        self.count_label = QLabel("")
        self.count_label.setObjectName("HintText")
        actions.addWidget(self.count_label)

        prev_page = QPushButton("◀ السابق")
        prev_page.clicked.connect(lambda: self._go(-1))
        next_page = QPushButton("التالي ▶")
        next_page.clicked.connect(lambda: self._go(1))
        actions.addWidget(prev_page)
        actions.addWidget(next_page)
        root.addLayout(actions)

        # ---- table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["العنوان", "القناة", "المصدر", "التصنيف", "المشاهدات", "الحالة", "التاريخ", ""]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 210)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.doubleClicked.connect(lambda *_: self._edit_selected())
        root.addWidget(self.table, 1)

    # ------------------------------------------------------------------ data
    def on_show(self, then: str | None = None) -> None:
        if then == "new":
            self._add_video()
        else:
            self.load()

    def refresh(self) -> None:
        self.load()

    def _query(self) -> str:
        from urllib.parse import quote

        q = quote(self.search_box.text().strip())
        status_value = self.status_filter.currentData() or ""
        sort_value = self.sort_select.currentData() or "newest"
        sp = f"?q={q}&status={status_value}&sort={sort_value}" if (q or status_value) else f"?sort={sort_value}"
        return f"/videos/admin/all{sp}&page={self.page}&page_size={self.config.page_size}"

    def load(self, page: int | None = None) -> None:
        if page is not None:
            self.page = max(1, min(page, max(self.pages, 1)))
        self.banner.hide()
        start_worker(
            self.client, "get",
            on_done=self._apply_rows, on_fail=self._fail,
            args=(self._query(),), kwargs={"auth": True},
            on_offline=lambda: self.banner.show(),
        )

    def _go(self, delta: int) -> None:
        target = self.page + delta
        if 1 <= target <= self.pages:
            self.load(page=target)

    def _apply_rows(self, data) -> None:
        items = data.get("items", [])
        meta = data.get("meta", {})
        self.total = meta.get("total", 0)
        self.pages = meta.get("pages", 1)
        self.count_label.setText(f"{self.total} عنصر — صفحة {meta.get('page')} / {self.pages}")

        self.table.setRowCount(0)
        for v in items:
            row = self.table.rowCount()
            self.table.insertRow(row)

            title_item = QTableWidgetItem(v["title"])
            title_item.setData(Qt.UserRole, v["id"])
            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, QTableWidgetItem(v.get("channel_name") or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(SOURCE_LABELS.get(v["source_type"], v["source_type"])))
            self.table.setItem(row, 3, QTableWidgetItem((v.get("category") or {}).get("name", "—")))

            views_item = QTableWidgetItem(f"{v['views_count']:,}")
            views_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, views_item)

            status_item = QTableWidgetItem(STATUS_LABELS.get(v["status"], v["status"]))
            color = {"published": "#10B981", "draft": "#F59E0B", "archived": "#64748B", "pending": "#3B82F6"}.get(v["status"], "#9CA3AF")
            status_item.setForeground(color)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, status_item)

            date_text = (v.get("published_at") or v.get("created_at") or "")[:10]
            self.table.setItem(row, 6, QTableWidgetItem(date_text))

            actions_widget = self._actions_row(v)
            self.table.setCellWidget(row, 6, actions_widget)

    def _actions_row(self, video: dict) -> QWidget:
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)

        vid = video["id"]

        def btn(text, handler, primary=False, danger=False):
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            if primary:
                b.setObjectName("Primary")
            if danger:
                b.setObjectName("Danger")
            b.setFixedHeight(26)
            b.clicked.connect(handler)
            return b

        is_published = video["status"] == "published"
        if is_published:
            lay.addWidget(btn("إلغاء النشر", lambda _, i=vid: self._lifecycle(i, "unpublish")))
        else:
            lay.addWidget(btn("نشر", lambda _, i=vid: self._lifecycle(i, "publish"), primary=True))
        lay.addWidget(btn("تعديل", lambda _, v=video: self._open_editor(v)))
        lay.addWidget(btn("نسخة", lambda _, i=vid: self._duplicate(i)))
        del_btn = btn("حذف", lambda _, v=video: self._delete_one(v))
        del_btn.setObjectName("Danger")
        lay.addWidget(del_btn)
        return widget

    # ------------------------------------------------------------------ actions
    def _selected_ids(self) -> list[int]:
        rows = {index.row() for index in self.table.selectionModel().selectedRows()}
        ids = []
        for r in rows:
            item = self.table.item(r, 0)
            if item:
                ids.append(item.data(Qt.UserRole))
        return [i for i in ids if i]

    def _add_video(self) -> None:
        dialog = VideoEditorDialog(self.client, parent=self)
        dialog.saved.connect(lambda: self.load())
        dialog.exec()

    def _edit_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if len(rows) != 1:
            return
        video_id = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        start_worker(
            self.client, "get",
            on_done=lambda detail: self._open_editor(detail),
            on_fail=self._fail,
            args=(f"/videos/{video_id}",), kwargs={"auth": True},
        )

    def _open_editor(self, video: dict) -> None:
        dialog = VideoEditorDialog(self.client, video=video, parent=self)
        dialog.saved.connect(lambda: self.load())
        dialog.exec()

    def _lifecycle(self, video_id: int, action: str) -> None:
        start_worker(
            self.client, "post",
            on_done=lambda d, a=action: self._after_action(d),
            on_fail=self._fail,
            args=(f"/videos/{video_id}/{action}",), kwargs={"json_body": None, "auth": True},
        )

    def _duplicate(self, video_id: int) -> None:
        start_worker(
            self.client, "post",
            on_done=lambda d: (show_toast(self.window(), "تم إنشاء نسخة كمسودة", "success"), self.load()),
            on_fail=self._fail,
            args=(f"/videos/{video_id}/duplicate",), kwargs={"json_body": None, "auth": True},
        )

    def _delete_one(self, video: dict) -> None:
        confirm = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف الفيديو:\n«{video['title']}»؟\n\nهذا الإجراء لا يمكن التراجع عنه.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        hard = False
        if video["status"] == "archived":
            answer = QMessageBox.question(
                self, "حذف نهائي؟",
                "الفيدو مؤرشف. هل تريد الحذف النهائي بدل النقل للمحذوفات؟",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            hard = answer == QMessageBox.Yes
        start_worker(
            self.client, "delete",
            on_done=lambda d: (show_toast(self.window(), "تم الحذف", "success"), self.load()),
            on_fail=self._fail,
            args=(f"/videos/{video['id']}?hard={str(hard).lower()}",),
            kwargs={"auth": True},
        )

    def _bulk(self, action: str) -> None:
        ids = self._selected_ids()
        if not ids:
            show_toast(self.window(), "لم يتم تحديد أي عنصر", "info")
            return
        if action == "delete":
            confirm = QMessageBox.question(
                self, "تأكيد الحذف الجماعي",
                f"سيتم نقل {len(ids)} فيديو إلى المحذوفات.\nهل تريد المتابعة؟",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
        payload = {"action": action, "ids": ids}
        start_worker(
            self.client, "post",
            on_done=lambda d: (show_toast(self.window(), d.get("message", "تم"), "success"), self.load()),
            on_fail=self._fail,
            args=("/videos/bulk",), kwargs={"json_body": payload, "auth": True},
        )

    def _after_action(self, result) -> None:
        message = result.get("message", "تم") if isinstance(result, dict) else "تم"
        show_toast(self.window(), message, "success")
        self.load()

    def _context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.addAction("فتح في المتصفح", self._open_in_browser)
        menu.addAction("تعديل...", lambda: self._edit_selected())
        menu.addSeparator()
        menu.addAction("تحديث القائمة", self.load)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _open_in_browser(self) -> None:
        import webbrowser

        rows = self.table.selectionModel().selectedRows()
        if len(rows) != 1:
            return
        video_id = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        webbrowser.open(f"{self.client.base_url()}/videos/{video_id}")

    def _fail(self, message: str) -> None:
        show_toast(self.window(), message, "error")

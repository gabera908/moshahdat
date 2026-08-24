"""Playlists management: CRUD + drag & drop ordering of videos (plan §19)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
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


class PlaylistsView(QWidget):
    def __init__(self, client: ApiClient, config: AppConfig):
        super().__init__()
        self.client = client
        self.config = config
        self.current_playlist: dict | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ---------------- left: playlists table
        left = QVBoxLayout()
        self.banner = OfflineBanner()
        left.addWidget(self.banner)

        bar = QHBoxLayout()
        add_btn = QPushButton("+ قائمة جديدة")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._create)
        bar.addWidget(add_btn)
        bar.addStretch()
        reload = QPushButton("تحديث")
        reload.clicked.connect(self.refresh)
        bar.addWidget(reload)
        left.addLayout(bar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["القائمة", "المعرّف", "عام؟", "عدد الفيديوهات"])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._load_selected_detail)
        left.addWidget(self.table, 1)
        root.addLayout(left, 3)

        # ---------------- right: playlist detail + ordered videos
        right = QVBoxLayout()

        self.detail_title = QLabel("اختر قائمة لعرض محتواها")
        self.detail_title.setStyleSheet("font-weight: 800; font-size: 15px;")
        right.addWidget(self.detail_title)

        tools = QHBoxLayout()
        add_video_btn = QPushButton("+ إضافة فيديو")
        add_video_btn.clicked.connect(self._add_video_dialog)
        remove_video_btn = QPushButton("إزالة المحدد")
        remove_video_btn.clicked.connect(self._remove_selected_video)
        save_order_btn = QPushButton("حفظ الترتيب")
        save_order_btn.setObjectName("Primary")
        save_order_btn.clicked.connect(self._save_order)
        delete_pl_btn = QPushButton("حذف القائمة")
        delete_pl_btn.setObjectName("Danger")
        delete_pl_btn.clicked.connect(self._delete_playlist)
        for b in (add_video_btn, remove_video_btn, save_order_btn):
            tools.addWidget(b)
        tools.addStretch()
        tools.addWidget(delete_pl_btn)
        right.addLayout(tools)

        self.video_list = QListWidget()
        self.video_list.setDragDropMode(QListWidget.InternalMove)
        self.video_list.setAlternatingRowColors(True)
        right.addWidget(self.video_list, 1)

        container = QWidget()
        container.setLayout(right)
        root.addWidget(container, 2)

    # ------------------------------------------------------------------ list
    def on_show(self) -> None:
        self.load()

    def refresh(self) -> None:
        self.load()

    def load(self) -> None:
        self.banner.hide()
        start_worker(
            self.client, "get",
            on_done=self._apply_rows, on_fail=self._fail,
            args=("/playlists?include_private=true&page_size=100",), kwargs={"auth": True},
            on_offline=lambda: self.banner.show(),
        )

    def _apply_rows(self, data) -> None:
        items = data.get("items", [])
        self.table.setRowCount(0)
        for p in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            title_item = QTableWidgetItem(p["title"])
            title_item.setData(Qt.UserRole, p["id"])
            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, QTableWidgetItem(p["slug"]))
            pub = QTableWidgetItem("نعم" if p["is_public"] else "لا (خاصة)")
            pub.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, pub)
            count = QTableWidgetItem(str(p.get("videos_count", 0)))
            count.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, count)

    # ------------------------------------------------------------------ detail
    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _load_selected_detail(self) -> None:
        pid = self._selected_id()
        if not pid:
            return
        start_worker(
            self.client, "get",
            on_done=self._show_detail, on_fail=self._fail,
            args=(f"/playlists/{pid}",), kwargs={"auth": True},
        )

    def _show_detail(self, playlist: dict) -> None:
        self.current_playlist = playlist
        self.detail_title.setText(f"🎬 {playlist['title']}")
        self.video_list.clear()
        for v in playlist.get("videos", []):
            item = QListWidgetItem(v["title"])
            item.setData(Qt.UserRole, v["id"])
            self.video_list.addItem(item)

    # ------------------------------------------------------------------ actions
    def _create(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        title, ok = QInputDialog.getText(self, "قائمة تشغيل جديدة", "العنوان:")
        if not ok or not title.strip():
            return
        start_worker(
            self.client, "post",
            on_done=lambda d: (show_toast(self.window(), "تم إنشاء القائمة", "success"), self.load()),
            on_fail=self._fail,
            args=("/playlists",), kwargs={"json_body": {"title": title.strip()}},
        )

    def _delete_playlist(self) -> None:
        pid = self.current_playlist["id"] if self.current_playlist else None
        if not pid:
            return
        confirm = QMessageBox.question(
            self, "تأكيد الحذف",
            f"حذف القائمة «{self.current_playlist['title']}»؟\nالفيديوهات نفسها لن تُحذف.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        start_worker(
            self.client, "delete",
            on_done=lambda d: (
                show_toast(self.window(), "تم حذف القائمة", "success"),
                setattr(self, "current_playlist", None),
                self.detail_title.setText("اختر قائمة لعرض محتواها"),
                self.video_list.clear(),
                self.load(),
            ),
            on_fail=self._fail,
            args=(f"/playlists/{pid}",),
        )

    def _ordered_ids(self) -> list[int]:
        return [
            self.video_list.item(i).data(Qt.UserRole)
            for i in range(self.video_list.count())
        ]

    def _save_order(self) -> None:
        if not self.current_playlist:
            show_toast(self.window(), "اختر قائمة أولًا", "info")
            return
        start_worker(
            self.client, "put",
            on_done=lambda d: (
                show_toast(self.window(), "تم حفظ الترتيب", "success"),
                self.load(),
            ),
            on_fail=self._fail,
            args=(f"/playlists/{self.current_playlist['id']}/videos",),
            kwargs={"json_body": {"video_ids": self._ordered_ids()}},
        )

    def _add_video_dialog(self) -> None:
        """Pick any video (published or draft) and append to the current playlist."""
        if not self.current_playlist:
            show_toast(self.window(), "اختر قائمة أولًا", "info")
            return
        # Use admin listing so drafts appear too — public listing hides drafts.
        start_worker(
            self.client, "get",
            on_done=self._pick_video, on_fail=self._fail,
            args=("/videos/admin/all?page_size=100&sort=newest",), kwargs={"auth": True},
        )

    def _pick_video(self, data) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout

        # Admin and public endpoints wrap differently: normalize to a flat list.
        raw = data.get("items", []) if isinstance(data, dict) else []
        # Public returns items; admin returns items inside data — both handled.
        if not raw and isinstance(data, dict) and "data" in data:
            raw = data["data"].get("items", [])
        existing = set(self._ordered_ids())
        candidates = [v for v in raw if v["id"] not in existing]
        if not candidates:
            show_toast(self.window(), "كل الفيديوهات موجودة في القائمة بالفعل", "info")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("اختر فيديو للإضافة")
        dialog.resize(500, 420)
        lay = QVBoxLayout(dialog)

        hint = QLabel("ابحث داخل القائمة ثم اختر فيديو واضغط موافق (نقر مزدوج يضيف مباشرة)")
        hint.setObjectName("HintText")
        lay.addWidget(hint)

        search = QLineEdit()
        search.setPlaceholderText("🔍 فلترة حسب العنوان...")
        lay.addWidget(search)

        picker = QListWidget()
        picker.setAlternatingRowColors(True)
        for v in candidates:
            label = v["title"]
            st = v.get("status", "")
            if st and st != "published":
                label += f"  — [{st}]"
            ch = v.get("channel_name")
            if ch:
                label += f"  • {ch}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, v["id"])
            picker.addItem(item)
        lay.addWidget(picker, 1)

        def _filter(text: str) -> None:
            q = text.strip().lower()
            for i in range(picker.count()):
                it = picker.item(i)
                it.setHidden(bool(q) and q not in it.text().lower())

        search.textChanged.connect(_filter)
        picker.itemDoubleClicked.connect(lambda _: dialog.accept())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        lay.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted or not picker.currentItem():
            return
        # When filtered, currentItem may be hidden — find first visible selected.
        chosen_item = picker.currentItem()
        if chosen_item.isHidden():
            for i in range(picker.count()):
                it = picker.item(i)
                if not it.isHidden() and it.isSelected():
                    chosen_item = it
                    break
        chosen = chosen_item.data(Qt.UserRole)

        ids = self._ordered_ids() + [chosen]
        start_worker(
            self.client, "put",
            on_done=lambda d: (show_toast(self.window(), "تمت الإضافة", "success"), self._load_selected_detail()),
            on_fail=self._fail,
            args=(f"/playlists/{self.current_playlist['id']}/videos",),
            kwargs={"json_body": {"video_ids": ids}},
        )

    def _remove_selected_video(self) -> None:
        row = self.video_list.currentRow()
        if row < 0 or not self.current_playlist:
            return
        self.video_list.takeItem(row)
        ids = self._ordered_ids()
        start_worker(
            self.client, "put",
            on_done=lambda d: show_toast(self.window(), "تمت الإزالة", "success"),
            on_fail=self._fail,
            args=(f"/playlists/{self.current_playlist['id']}/videos",),
            kwargs={"json_body": {"video_ids": ids}},
        )
        self._load_selected_detail()

    def _fail(self, message: str) -> None:
        show_toast(self.window(), message, "error")

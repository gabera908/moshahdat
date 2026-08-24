"""Add/Edit video dialog with URL checking and provider preview (plan §7)."""
from urllib.parse import quote

from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient, start_worker
from widgets.common import show_toast

SOURCE_TYPES = [
    ("youtube", "YouTube"),
    ("gdrive", "Google Drive"),
    ("vimeo", "Vimeo"),
    ("dropbox", "Dropbox"),
    ("direct", "رابط مباشر"),
    ("embed", "Embed URL"),
]


class VideoEditorDialog(QDialog):
    saved = Signal()

    def __init__(self, client: ApiClient, video: dict | None = None, parent=None):
        super().__init__(parent)
        self.client = client
        self.video = video
        self.checked_info: dict | None = None

        self.setWindowTitle("تعديل فيديو" if video else "إضافة فيديو جديد")
        self.resize(640, 620)
        self._categories: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        # ---- source row
        source_row = QHBoxLayout()
        self.source_select = QComboBox()
        for value, label in SOURCE_TYPES:
            self.source_select.addItem(label, value)
        source_row.addWidget(self.source_select, 2)
        form.addRow("مصدر الفيديو:", source_row)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "https://www.youtube.com/watch?v=... أو رابط MP4 مباشر"
        )
        check_btn = QPushButton("فحص الرابط")
        check_btn.setObjectName("Primary")
        check_btn.setCursor(Qt.PointingHandCursor)
        check_btn.clicked.connect(self._check_url)
        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(check_btn)
        container = QWidget()
        container.setLayout(url_row)
        form.addRow("الرابط:", container)

        # check result feedback
        self.check_result = QLabel("")
        self.check_result.setWordWrap(True)
        form.addRow("", self.check_result)

        # preview thumbnail + embed hint
        preview_row = QHBoxLayout()
        self.preview_label = QLabel("أضف رابطًا واضغط «فحص الرابط» لعرض المعاينة")
        self.preview_label.setObjectName("HintText")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(90)
        self.preview_label.setStyleSheet(
            "border:1px dashed #2C313B; border-radius:10px; padding:8px;"
        )
        preview_row.addWidget(self.preview_label, 1)
        form.addRow("معاينة:", preview_row)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("عنوان الفيديو")
        form.addRow("العنوان:", self.title_input)

        self.description_input = QPlainTextEdit()
        self.description_input.setPlaceholderText("وصف مختصر للفيديو...")
        self.description_input.setMaximumHeight(96)
        form.addRow("الوصف:", self.description_input)

        self.category_select = QComboBox()
        self.category_select.addItem("بدون تصنيف", "")
        form.addRow("التصنيف:", self.category_select)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("وسوم مفصولة بفواصل، مثال: بيئة, مناخ")
        form.addRow("Tags:", self.tags_input)

        self.thumbnail_input = QLineEdit()
        self.thumbnail_input.setPlaceholderText("اتركه فارغًا ليُجلب تلقائيًا إن أمكن")
        form.addRow("صورة مصغرة:", self.thumbnail_input)

        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("بالثواني — اختياري")
        form.addRow("المدة:", self.duration_input)

        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("اسم القناة أو المنتج — اختياري")
        form.addRow("القناة:", self.channel_input)

        self.publish_date = QDateEdit()
        self.publish_date.setCalendarPopup(True)
        self.publish_date.setDisplayFormat("yyyy-MM-dd")
        self.publish_date.setDate(QDate.currentDate())
        form.addRow("تاريخ النشر:", self.publish_date)

        root.addLayout(form)

        self.featured_check = QCheckBox("فيديو مميز (يظهر في الصفحة الرئيسية)")
        root.addWidget(self.featured_check)

        buttons = QHBoxLayout()
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        buttons.addStretch()
        self.save_draft_btn = QPushButton("حفظ كمسودة")
        self.save_draft_btn.clicked.connect(lambda: self._save(publish=False))
        buttons.addWidget(self.save_draft_btn)
        self.publish_btn = QPushButton("نشر الفيديو")
        self.publish_btn.setObjectName("Primary")
        self.publish_btn.clicked.connect(lambda: self._save(publish=True))
        buttons.addWidget(self.publish_btn)
        root.addLayout(buttons)

        self._orig_publish_date = None
        if video:
            self._fill_from_video(video)

        start_worker(
            client, "get",
            on_done=self._apply_categories, on_fail=lambda m: None,
            args=("/categories",), kwargs={"auth": True},
        )

    # ------------------------------------------------------------------ helpers
    def _apply_categories(self, data) -> None:
        items = data.get("items", []) if isinstance(data, dict) else []
        self._categories = items
        current = ""
        if self.video:
            cat = self.video.get("category") or {}
            current = str(cat.get("id", ""))
        elif getattr(self, "_pending_category_id", None):
            current = str(self._pending_category_id)
        self.category_select.clear()
        self.category_select.addItem("بدون تصنيف", "")
        for c in items:
            self.category_select.addItem(c["name"], c["id"])
            if str(c["id"]) == current:
                self.category_select.setCurrentIndex(self.category_select.count() - 1)

    def _fill_from_video(self, v: dict) -> None:
        index = self.source_select.findData(v.get("source_type"))
        if index >= 0:
            self.source_select.setCurrentIndex(index)
        self.url_input.setText(v.get("source_url", ""))
        self.title_input.setText(v.get("title", ""))
        self.description_input.setPlainText(v.get("description") or "")
        thumb = v.get("thumbnail_url") or ""
        self.thumbnail_input.setText(thumb)
        duration = v.get("duration")
        self.duration_input.setText(str(duration) if duration else "")
        self.channel_input.setText(v.get("channel_name") or "")
        pub = (v.get("published_at") or "")[:10]
        if pub:
            parsed = QDate.fromString(pub, "yyyy-MM-dd")
            if parsed.isValid():
                self.publish_date.setDate(parsed)
        self._orig_publish_date = self.publish_date.date().toString("yyyy-MM-dd")
        self.featured_check.setChecked(bool(v.get("is_featured")))
        tag_names = ", ".join(t["name"] for t in v.get("tags", []))
        self.tags_input.setText(tag_names)
        self._set_preview(thumb, v.get("embed_url"))
        self.video_id = v["id"]

    def _check_url(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            self._show_check("⚠ أدخل رابطًا أولًا.", error=True)
            return
        self._show_check("⏳ جارٍ فحص الرابط...")
        start_worker(
            self.client, "post_raw",
            on_done=self._apply_check, on_fail=self._check_fail,
            args=("/videos/check-url",),
            kwargs={"json_body": {"url": url}},
        )

    def _apply_check(self, data) -> None:
        """`data` is the full envelope body for this endpoint."""
        valid = bool(data.get("valid"))
        message = data.get("message", "")
        info = data.get("data") or {}
        if not valid:
            self._show_check(f"✗ {message}", error=True)
            return

        source_key = info.get("source_type")
        idx = self.source_select.findData(source_key)
        if idx >= 0:
            self.source_select.setCurrentIndex(idx)

        embed = info.get("embed_url") or ""
        thumb = info.get("thumbnail_url")
        mode = info.get("playable_mode", "")

        if not self.title_input.text().strip():
            pass  # keep admin-entered title; providers don't fetch titles in MVP
        if thumb and not self.thumbnail_input.text().strip():
            self.thumbnail_input.setText(thumb)
        suggested = info.get("suggested_title")
        if suggested and not self.title_input.text().strip():
            self.title_input.setText(suggested)
        self._set_preview(thumb, embed)
        self._show_check(f"✓ {message} [{mode}]")

    def _check_fail(self, message: str) -> None:
        self._show_check(f"✗ {message}", error=True)

    def _set_preview(self, thumb: str | None, embed: str | None) -> None:
        parts = []
        if embed:
            short = embed if len(embed) <= 70 else embed[:67] + "..."
            parts.append(f"▶ {short}")
        if thumb:
            parts.append(f"🖼 صورة مصغرة متوفرة")
        self.preview_label.setText("\n".join(parts) or "لا تتوفر معاينة لهذا المصدر")
        self.checked_info = {"embed_url": embed, "thumbnail_url": thumb}

    def _show_check(self, text: str, error: bool = False) -> None:
        self.check_result.setText(text)
        color = "#F87171" if error else "#34D399"
        self.check_result.setStyleSheet(f"color: {color}; font-weight: 600;")

    def _collect_tags(self) -> list[str]:
        raw = self.tags_input.text().strip()
        return [t.strip() for t in raw.split(",") if t.strip()] if raw else []

    def _save(self, publish: bool) -> None:
        title = self.title_input.text().strip()
        url = self.url_input.text().strip()
        if not title:
            show_toast(self.window(), "أدخل عنوان الفيديو", "error")
            return
        if not url:
            show_toast(self.window(), "أدخل رابط الفيديو", "error")
            return

        payload = {
            "title": title,
            "description": self.description_input.toPlainText().strip() or None,
            "source_type": self.source_select.currentData(),
            "source_url": url,
            "thumbnail_url": self.thumbnail_input.text().strip() or None,
            "duration": int(self.duration_input.text()) if self.duration_input.text().strip().isdigit() else None,
            "category_id": self.category_select.currentData() or None,
            "status": "published" if publish else "draft",
            "is_featured": self.featured_check.isChecked(),
        }
        payload["channel_name"] = self.channel_input.text().strip() or None

        chosen = self.publish_date.date().toString("yyyy-MM-dd")
        is_edit = getattr(self, "video_id", None) is not None
        if publish:
            changed = getattr(self, "_orig_publish_date", None) not in (None, chosen)
            if not is_edit or changed:
                payload["published_at"] = f"{chosen}T12:00:00Z"

        is_edit = getattr(self, "video_id", None) is not None
        if is_edit:
            path = f"/videos/{self.video_id}"
            method = "put"
        else:
            path = "/videos"
            method = "post"

        def _after(result) -> None:
            message = result.get("message", "تم الحفظ") if isinstance(result, dict) else "تم الحفظ"
            show_toast(self.window(), message, "success")
            self.saved.emit()
            self.accept()

        start_worker(
            self.client, method,
            on_done=_after, on_fail=lambda m: show_toast(self.window(), m, "error"),
            args=(path,) if method == "post" else (path,),
            kwargs={"json_body": payload} if method == "post" else {"json_body": payload},
        )

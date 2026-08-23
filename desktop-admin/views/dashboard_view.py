"""Dashboard view: stat cards + charts."""
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient, start_worker
from config import AppConfig
from widgets.common import BarChart, OfflineBanner, StatCard


class DashboardView(QWidget):
    def __init__(self, client: ApiClient, config: AppConfig):
        super().__init__()
        self.client = client
        self.config = config

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        self.banner = OfflineBanner()
        root.addWidget(self.banner)

        # ---- stat cards
        grid = QGridLayout()
        grid.setSpacing(12)
        self.cards = {
            "total_videos": StatCard("إجمالي الفيديوهات", accent="#B87333"),
            "published_videos": StatCard("المنشورة", accent="#10B981"),
            "draft_videos": StatCard("المسودات", accent="#F59E0B"),
            "total_views": StatCard("إجمالي المشاهدات", accent="#3B82F6"),
            "views_today": StatCard("مشاهدات اليوم", accent="#8B5CF6"),
            "total_categories": StatCard("التصنيفات", accent="#EC4899"),
            "total_playlists": StatCard("قوائم التشغيل", accent="#14B8A6"),
            "archived_videos": StatCard("المؤرشفة", accent="#64748B"),
        }
        for i, (_, card) in enumerate(self.cards.items()):
            grid.addWidget(card, i // 4, i % 4)
        root.addLayout(grid)

        # ---- charts row
        charts = QHBoxLayout()
        charts.setSpacing(16)

        views_box = QVBoxLayout()
        chart_title = QLabel("المشاهدات (آخر 30 يومًا)")
        chart_title.setStyleSheet("font-weight: 700;")
        views_box.addWidget(chart_title)
        self.daily_chart = BarChart()
        views_box.addWidget(self.daily_chart)

        source_box = QVBoxLayout()
        source_label = QLabel("توزيع الفيديوهات حسب المصدر")
        source_label.setStyleSheet("font-weight: 700;")

        # Simple proportional bars for sources
        self.source_layout = QVBoxLayout()
        self.source_layout.setSpacing(8)

        source_box.addWidget(source_label)
        source_box.addLayout(self.source_layout)
        source_box.addStretch(1)

        charts.addLayout(views_box, 3)
        charts.addLayout(source_box, 2)
        root.addLayout(charts, 1)

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        self.banner.hide()
        start_worker(
            self.client, "get",
            on_done=self._apply_stats, on_fail=self._fail,
            args=("/analytics/dashboard",),
            kwargs={"auth": True},
            on_offline=lambda: self.banner.show(),
        )
        start_worker(
            self.client, "get",
            on_done=self._apply_daily, on_fail=lambda *_: None,
            args=("/analytics/views/daily?days=30",),
            kwargs={"auth": True},
        )
        start_worker(
            self.client, "get",
            on_done=self._apply_sources, on_fail=lambda *_: None,
            args=("/analytics/by-source",),
            kwargs={"auth": True},
        )

    def _apply_stats(self, data) -> None:
        for key, card in self.cards.items():
            value = data.get(key, 0) if isinstance(data, dict) else 0
            card.set_value(f"{value:,}" if isinstance(value, int) else str(value))

    def _fail(self, message: str) -> None:
        from widgets.common import show_toast

        show_toast(self.window(), message, "error")

    def _apply_daily(self, data) -> None:
        points = [
            (item["date"][5:], item["views"])  # MM-DD label
            for item in data.get("items", [])
        ]
        self.daily_chart.set_data(points)

    _SOURCE_LABELS = {
        "youtube": "YouTube",
        "gdrive": "Google Drive",
        "vimeo": "Vimeo",
        "dropbox": "Dropbox",
        "direct": "رابط مباشر",
        "embed": "Embed URL",
    }

    def _apply_sources(self, data) -> None:
        # clear old rows
        while self.source_layout.count():
            item = self.source_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = data.get("items", []) if isinstance(data, dict) else []
        total = sum(i["count"] for i in items) or 1
        palette = ["#B87333", "#3B82F6", "#10B981", "#F59E0B", "#EC4899", "#14B8A6"]

        for idx, item in enumerate(items[:6]):
            label = self._SOURCE_LABELS.get(item["source_type"], item["source_type"])
            pct = round(item["count"] / total * 100)

            row = QHBoxLayout()
            name = QLabel(f"{label} — {item['count']}")
            name.setStyleSheet("font-size: 12px; color:#9CA3AF;")
            row.addWidget(name)
            row.addStretch()

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(pct)
            bar.setTextVisible(False)
            bar.setFixedHeight(10)
            bar.setStyleSheet(
                f"""
                QProgressBar {{ background:#12151B; border:none; border-radius:5px; }}
                QProgressBar::chunk {{ background:{palette[idx % len(palette)]}; border-radius:5px; }}
                """
            )
            row.addWidget(bar, 2)
            pct_label = QLabel(f"{pct}%")
            pct_label.setStyleSheet("font-size:11px; color:#6B7280;")
            row.addWidget(pct_label)

            container = QWidget()
            container.setLayout(row)
            self.source_layout.addWidget(container)

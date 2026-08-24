"""Main window: sidebar navigation + stacked content views."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiClient
from config import AppConfig
from utils.logging_setup import log
from views.dashboard_view import DashboardView
from views.logs_view import LogsView
from views.playlists_view import PlaylistsView
from views.settings_view import SettingsView
from views.tags_view import TagsView
from views.users_view import UsersView
from views.videos_view import VideosView

NAV_ITEMS = [
    ("dashboard", "الرئيسية"),
    ("videos", "الفيديوهات"),
    ("categories", "التصنيفات"),
    ("tags", "Tags"),
    ("playlists", "قوائم التشغيل"),
    ("users", "المستخدمون"),
    ("logs", "سجل العمليات"),
    ("settings", "الإعدادات"),
]


class MainWindow(QMainWindow):
    def __init__(self, client: ApiClient, config: AppConfig, username: str):
        super().__init__()
        self.client = client
        self.config = config
        self.username = username

        self.setWindowTitle(f"منصة الفيديو — لوحة الإدارة ({username})")
        self.resize(1280, 780)
        self.setMinimumSize(1000, 640)

        root = QWidget()
        root.setObjectName("Root")
        root_lay = QHBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        self.setCentralWidget(root)

        # ---------------- Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(14, 20, 14, 16)
        side_lay.setSpacing(4)

        logo = QLabel("🎬 منصة الفيديو")
        logo.setObjectName("AppTitle")
        logo.setAlignment(Qt.AlignCenter)
        side_lay.addWidget(logo)
        side_lay.addSpacing(18)

        self.nav_buttons: dict[str, QPushButton] = {}
        for key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.navigate(k))
            side_lay.addWidget(btn)
            self.nav_buttons[key] = btn

        side_lay.addStretch()

        user_chip = QLabel(f"👤 {username}")
        user_chip.setObjectName("HintText")
        user_chip.setAlignment(Qt.AlignCenter)
        side_lay.addWidget(user_chip)

        logout_btn = QPushButton("تسجيل الخروج")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(self._logout)
        side_lay.addWidget(logout_btn)

        # ---------------- Content area
        content = QFrame()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("Topbar")
        topbar.setFixedHeight(56)
        top_lay = QHBoxLayout(topbar)
        top_lay.setContentsMargins(24, 0, 24, 0)

        self.page_title = QLabel("الرئيسية")
        self.page_title.setObjectName("SectionTitle")
        top_lay.addWidget(self.page_title)
        top_lay.addStretch()

        hint = QLabel("Ctrl+N فيديو جديد · F5 تحديث")
        hint.setObjectName("HintText")
        top_lay.addWidget(hint)

        self.stack = QStackedWidget()

        self.views = {
            "dashboard": DashboardView(client, config),
            "videos": VideosView(client, config),
            "categories": self._placeholder_categories(),
            "tags": TagsView(client, config),
            "playlists": PlaylistsView(client, config),
            "users": UsersView(client, config),
            "logs": LogsView(client, config),
            "settings": SettingsView(client, config),
        }

        # Every page scrolls to its end (plan §30: reach bottom of page)
        self.scrolls = {}
        for key, view in self.views.items():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(view)
            self.scrolls[key] = scroll
            self.stack.addWidget(scroll)

        content_lay.addWidget(topbar)
        content_lay.addWidget(self.stack)
        root_lay.addWidget(sidebar)
        root_lay.addWidget(content, 1)

        # ---------------- Shortcuts (plan §30)
        new_video = QAction(self)
        new_video.setShortcut(QKeySequence("Ctrl+N"))
        new_video.triggered.connect(lambda: self.navigate("videos", then="new"))
        self.addAction(new_video)

        refresh = QAction(self)
        refresh.setShortcut(QKeySequence("F5"))
        refresh.triggered.connect(self._refresh_current)
        self.addAction(refresh)

        find_action = QAction(self)
        find_action.setShortcut(QKeySequence("Ctrl+F"))
        find_action.triggered.connect(self._focus_search)
        self.addAction(find_action)

        self.current_key = ""
        self.navigate("dashboard")

    # ------------------------------------------------------------------ nav
    def _placeholder_categories(self):
        from views.categories_view import CategoriesView

        return CategoriesView(self.client, self.config)

    def navigate(self, key: str, then: str | None = None) -> None:
        if key not in self.views:
            return
        self.current_key = key
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)

        title = dict(NAV_ITEMS)[key]
        if key == "videos" and then == "new":
            title = "إضافة فيديو"
        self.page_title.setText(title)

        self.stack.setCurrentWidget(self.scrolls[key])
        view = self.views[key]
        if hasattr(view, "on_show"):
            view.on_show(then=then) if then else view.on_show()

    def _refresh_current(self) -> None:
        view = self.views.get(self.current_key)
        if hasattr(view, "refresh"):
            view.refresh()

    def _focus_search(self) -> None:
        view = self.views.get(self.current_key)
        search_box = getattr(view, "search_box", None)
        if search_box:
            search_box.setFocus()

    def _logout(self) -> None:
        log.info("logout user=%s", self.username)
        self.client.logout()
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802
        event.accept()

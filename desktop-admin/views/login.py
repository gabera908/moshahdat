"""Login dialog: JWT authentication against the backend."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from api_client import ApiClient, ApiWorker
from config import AppConfig
from utils.logging_setup import log


class LoginDialog(QDialog):
    def __init__(self, client: ApiClient, config: AppConfig):
        super().__init__()
        self.client = client
        self.config = config

        self.setWindowTitle("تسجيل الدخول — لوحة إدارة المنصة")
        self.setFixedSize(400, 330)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(14)

        title = QLabel("منصة الفيديو")
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("لوحة الإدارة — تسجيل الدخول")
        subtitle.setObjectName("MutedText")
        subtitle.setAlignment(Qt.AlignCenter)

        form = QFormLayout()
        form.setSpacing(10)

        self.username = QLineEdit()
        self.username.setPlaceholderText("اسم المستخدم")
        if config.remember_username and config.saved_username:
            self.username.setText(config.saved_username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("كلمة المرور")
        self.password.setEchoMode(QLineEdit.Password)

        form.addRow("المستخدم:", self.username)
        form.addRow("كلمة المرور:", self.password)

        self.remember = QCheckBox("تذكر اسم المستخدم")
        if config.remember_username and config.saved_username:
            self.remember.setChecked(True)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #F87171; font-weight: 600;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.login_btn = QPushButton("تسجيل الدخول")
        self.login_btn.setObjectName("Primary")

        self.server_row = QHBoxLayout()
        server_label = QLabel("الخادم:")
        server_label.setObjectName("HintText")
        self.server_input = QLineEdit(config.api_base_url)
        self.server_row.addWidget(server_label)
        self.server_row.addWidget(self.server_input, 1)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(6)
        root.addLayout(form)
        root.addWidget(self.remember)
        root.addWidget(self.error_label)
        root.addSpacing(4)
        root.addWidget(self.login_btn)
        root.addStretch(1)
        root.addLayout(self.server_row)

        self.login_btn.clicked.connect(self._do_login)
        self.password.returnPressed.connect(self._do_login)
        self.username.returnPressed.connect(self.password.setFocus)

        self._worker = None

    def _do_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self._show_error("أدخل اسم المستخدم وكلمة المرور.")
            return

        base = self.server_input.text().strip().rstrip("/")
        if base:
            self.client.set_base_url(base)

        self.login_btn.setEnabled(False)
        self.login_btn.setText("جارٍ التحقق...")
        self._hide_error()

        self._worker = ApiWorker(
            self.client, "login", args=(username, password),
        )
        self._worker.signals.finished.connect(self._on_success)
        self._worker.signals.failed.connect(self._on_fail)
        self._worker.start()

    def _on_success(self, _tokens) -> None:
        log.info("login success user=%s", self.username.text())
        if self.remember.isChecked():
            self.config.saved_username = self.username.text().strip()
        self.config.remember_username = self.remember.isChecked()
        self.config.save()
        self.accept()

    def _on_fail(self, message: str) -> None:
        log.warning("login failed: %s", message.replace("\n", " "))
        self.login_btn.setEnabled(True)
        self.login_btn.setText("تسجيل الدخول")
        self._show_error(message)

    def _show_error(self, msg: str) -> None:
        self.error_label.setText(msg)
        self.error_label.show()

    def _hide_error(self) -> None:
        self.error_label.hide()

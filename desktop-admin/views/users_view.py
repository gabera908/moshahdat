"""Users management (admin only): CRUD + role + reset password."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
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

ROLE_LABELS = {"admin": "مدير", "editor": "محرر", "moderator": "مشرف"}


class UsersView(QWidget):
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
        add_btn = QPushButton("+ مستخدم جديد")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add)
        bar.addWidget(add_btn)
        bar.addStretch()
        reload = QPushButton("تحديث")
        reload.clicked.connect(self.refresh)
        bar.addWidget(reload)
        root.addLayout(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["المستخدم", "البريد", "الدور", "نشط؟", ""])
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

    def on_show(self) -> None:
        self.load()

    def refresh(self) -> None:
        self.load()

    def load(self) -> None:
        self.banner.hide()
        start_worker(
            self.client, "get",
            on_done=self._apply_rows, on_fail=self._fail,
            args=("/users?page_size=100",), kwargs={"auth": True},
            on_offline=lambda: self.banner.show(),
        )

    def _apply_rows(self, data) -> None:
        items = data.get("items", [])
        self._items = items
        self.table.setRowCount(0)
        for u in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name_item = QTableWidgetItem(f"{u['username']} — {u.get('full_name') or ''}")
            name_item.setData(Qt.UserRole, u["id"])
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(u["email"]))
            role_item = QTableWidgetItem(ROLE_LABELS.get(u["role"], u["role"]))
            role_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, role_item)
            active = QTableWidgetItem("نعم" if u["is_active"] else "معطل")
            active.setTextAlignment(Qt.AlignCenter)
            active.setForeground(QColor("#34D399" if u["is_active"] else "#F87171"))
            self.table.setItem(row, 3, active)

            actions = QWidget()
            lay = QHBoxLayout(actions)
            lay.setContentsMargins(4, 2, 4, 2)
            uid = u["id"]
            username = u["username"]
            is_active = u["is_active"]

            edit_b = QPushButton("تعديل الدور")
            pass_b = QPushButton("كلمة مرور")
            toggle_b = QPushButton("تعطيل" if is_active else "تفعيل")
            del_b = QPushButton("حذف")
            del_b.setObjectName("Danger")
            edit_b.clicked.connect(lambda _, i=uid: self._edit_role(i))
            pass_b.clicked.connect(lambda _, i=uid: self._reset_password(i))
            toggle_b.clicked.connect(lambda _, i=uid, a=is_active: self._toggle_active(i, not a))
            del_b.clicked.connect(lambda _, n=username, i=uid: self._delete(n, i))
            for b in (edit_b, pass_b, toggle_b, del_b):
                b.setFixedHeight(26)
                lay.addWidget(b)

            self.table.setCellWidget(row, 4, actions)

    # ------------------------------------------------------------------ actions
    def _edit_role(self, uid: int) -> None:
        user = next((u for u in getattr(self, "_items", []) if u["id"] == uid), None)
        if not user:
            return
        roles = list(ROLE_LABELS.keys())
        labels = [ROLE_LABELS[r] for r in roles]
        current = roles.index(user["role"]) if user["role"] in roles else 0

        choice, ok = QInputDialog.getItem(
            self, "تعديل المستخدم",
            f"دور «{user['username']}»:", labels, current, False,
        )
        if not ok:
            return
        payload = {"role": roles[labels.index(choice)]}
        start_worker(
            self.client, "put",
            on_done=lambda d: (show_toast(self.window(), "تم التحديث", "success"), self.load()),
            on_fail=self._fail,
            args=(f"/users/{uid}",), kwargs={"json_body": payload},
        )

    def _toggle_active(self, uid: int, new_state: bool) -> None:
        start_worker(
            self.client, "put",
            on_done=lambda d: (show_toast(self.window(), "تم التحديث", "success"), self.load()),
            on_fail=self._fail,
            args=(f"/users/{uid}",), kwargs={"json_body": {"is_active": new_state}},
        )

    def _reset_password(self, uid: int) -> None:
        text, ok = QInputDialog.getText(
            self, "إعادة تعيين كلمة المرور",
            "كلمة المرور الجديدة (8 أحرف على الأقل، حروف وأرقام):",
        )
        text = (text or "").strip()
        if not ok:
            return
        if len(text) < 8 or not any(c.isdigit() for c in text) or not any(c.isalpha() for c in text):
            show_toast(self.window(), "كلمة المرور ضعيفة: حروف + أرقام و8 أحرف على الأقل", "error")
            return
        start_worker(
            self.client, "put",
            on_done=lambda d: show_toast(self.window(), "تم تعيين كلمة المرور", "success"),
            on_fail=self._fail,
            args=(f"/users/{uid}/password",), kwargs={"json_body": {"new_password": text}},
        )

    def _delete(self, username: str, uid: int) -> None:
        confirm = QMessageBox.question(
            self, "تأكيد الحذف",
            f"حذف المستخدم «{username}» نهائيًا؟\nهذا الإجراء لا يمكن التراجع عنه.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        start_worker(
            self.client, "delete",
            on_done=lambda d: (show_toast(self.window(), "تم الحذف", "success"), self.load()),
            on_fail=self._fail,
            args=(f"/users/{uid}",),
        )

    def _add(self) -> None:
        dialog = UserCreateDialog(self.client, parent=self)
        dialog.created.connect(lambda: self.load())
        dialog.exec()

    def _fail(self, message: str) -> None:
        show_toast(self.window(), message, "error")


class UserCreateDialog(QDialog):
    created = Signal()

    def __init__(self, client: ApiClient, parent=None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle("مستخدم جديد")
        self.resize(400, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.username_input = QLineEdit()
        self.full_name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.role_select = QComboBox()
        for value, label in ROLE_LABELS.items():
            self.role_select.addItem(label, value)

        form.addRow("المستخدم:", self.username_input)
        form.addRow("الاسم الكامل:", self.full_name_input)
        form.addRow("البريد:", self.email_input)
        form.addRow("كلمة المرور:", self.password_input)
        form.addRow("الدور:", self.role_select)

        save_btn = QPushButton("إنشاء")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)

        layout.addLayout(form)
        layout.addWidget(save_btn)

    def _save(self) -> None:
        payload = {
            "username": self.username_input.text().strip(),
            "email": self.email_input.text().strip(),
            "password": self.password_input.text(),
            "full_name": self.full_name_input.text().strip() or None,
            "role": self.role_select.currentData(),
        }
        if not payload["username"] or not payload["email"] or len(payload["password"]) < 8:
            show_toast(self.window(), "أكمل البيانات (وكلمة مرور 8 أحرف على الأقل)", "error")
            return
        start_worker(
            self.client, "post",
            on_done=lambda d: (
                show_toast(self.window(), "تم إنشاء المستخدم", "success"),
                self.created.emit(),
                self.accept(),
            ),
            on_fail=lambda m: show_toast(self.window(), m, "error"),
            args=("/users",), kwargs={"json_body": payload},
        )

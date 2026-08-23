"""Reusable custom widgets: stat cards, toasts, bar chart, offline banner."""
from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class StatCard(QFrame):
    """Dashboard metric card."""

    def __init__(self, title: str, value: str = "—", accent: str = "#B87333", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setStyleSheet(
            f"""
            QFrame#StatCard {{
                background-color: #181B21;
                border: 1px solid #23272F;
                border-radius: 14px;
            }}
            """
        )
        self.setMinimumHeight(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        self._title = QLabel(title)
        self._title.setObjectName("MutedText")
        self._title.setStyleSheet("font-size: 12px; color: #9CA3AF; border: none; background: transparent;")

        self._value = QLabel(value)
        self._value.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {accent}; border: none; background: transparent;")

        layout.addWidget(self._title)
        layout.addWidget(self._value)

    def set_value(self, value: str) -> None:
        self._value.setText(str(value))


class Toast(QWidget):
    """Floating notification bubble (auto-dismisses)."""

    INFO = "#3B82F6"
    SUCCESS = "#10B981"
    ERROR = "#EF4444"

    def __init__(self, parent: QWidget, message: str, kind: str = "info", duration_ms: int = 3200):
        super().__init__(parent)
        colors = {"success": Toast.SUCCESS, "error": Toast.ERROR}
        color = colors.get(kind, Toast.INFO)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        frame = QFrame(self)
        frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: #1D2129;
                border: 1px solid {color};
                border-radius: 10px;
            }}
            QLabel {{ color: white; font-size: 13px; background: transparent; border: none; }}
            """
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.addWidget(QLabel(message))

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)
        self.adjustSize()

    def popup(self) -> None:
        parent = self.parentWidget()
        if parent:
            x = parent.width() - self.width() - 28
            y = parent.height() - self.height() - 40
            self.move(QPoint(x, y))
        self.show()

        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(3500)
        anim.setKeyValueAt(0.86, 1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutQuad)
        anim.finished.connect(self.close)
        anim.start()
        self._anim = anim


def show_toast(parent: QWidget, message: str, kind: str = "info") -> None:
    Toast(parent, message, kind).popup()


class BarChart(QWidget):
    """Lightweight dependency-free vertical bar chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._points: list[tuple[str, int]] = []
        self.bar_color = QColor("#B87333")

    def set_data(self, points: list[tuple[str, int]]) -> None:
        self._points = points
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        pad_l, pad_b, pad_t = 8, 22, 10

        if not self._points:
            painter.setPen(QPen(QColor("#6B7280")))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "لا توجد بيانات")
            return

        max_v = max(v for _, v in self._points) or 1
        n = len(self._points)
        slot = max(4.0, (w - pad_l * 2) / n)
        bar_w = min(slot * 0.62, 34.0)
        base_y = h - pad_b
        chart_h = h - pad_b - pad_t

        # baseline
        painter.setPen(QPen(QColor("#23272F"), 1))
        painter.drawLine(pad_l, int(base_y), int(w - pad_l), int(base_y))

        gradient_colors = [QColor("#CB8840"), QColor("#B87333"), QColor("#9A5F28")]

        for i, (label, value) in enumerate(self._points):
            x_center = pad_l + slot * i + slot / 2
            bh = (value / max_v) * chart_h if value else 2
            rect = QRectF(x_center - bar_w / 2, base_y - bh, bar_w, bh)
            color = gradient_colors[min(i % 3, len(gradient_colors) - 1)]
            color.setAlpha(230)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 3, 3)

            # label every few bars when dense
            step = max(1, n // 8)
            if i % step == 0:
                painter.setPen(QPen(QColor("#6B7280")))
                small_font = painter.font()
                small_font.setPointSize(7)
                painter.setFont(small_font)
                painter.drawText(
                    QRectF(x_center - slot / 2, base_y + 4, slot, 14),
                    Qt.AlignCenter,
                    label,
                )

        painter.end()


class OfflineBanner(QFrame):
    """Sticky banner shown when the server cannot be reached."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background-color: rgba(239,68,68,0.14);
                border: 1px solid rgba(239,68,68,0.5);
                border-radius: 10px;
            }
            QLabel { color: #FCA5A5; font-weight: 700; background: transparent; border: none; }
            """
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 9, 14, 9)
        icon = QLabel("⚠")
        msg = QLabel("لا يوجد اتصال بالخادم — تحقق من الإنترنت أو إعدادات الاتصال.")
        lay.addWidget(icon)
        lay.addWidget(msg)
        lay.addStretch()
        self.hide()

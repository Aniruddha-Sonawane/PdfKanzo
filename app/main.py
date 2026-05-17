import ctypes
import os
import sys

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import (
    QGuiApplication,
    QIcon,
    QPixmap,
)
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QLabel,
    QWidget,
)

from ui.main_window import MainWindow

APP_ID = "PdfKanzo.Desktop.App"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset_path(*parts: str) -> str:
    return os.path.join(BASE_DIR, "assets", *parts)


# ─────────────────────────────────────────────────────────────────────────────
#  Splash screen
# ─────────────────────────────────────────────────────────────────────────────


class SplashScreen(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.logo = QLabel(self)
        pixmap = QPixmap(asset_path("icons", "logo.png"))
        pixmap = pixmap.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())
        self._center()

        effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(effect)

    def _center(self):
        geo = QGuiApplication.primaryScreen().availableGeometry()
        self.move(
            (geo.width() - self.width()) // 2,
            (geo.height() - self.height()) // 2,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Animation helper
# ─────────────────────────────────────────────────────────────────────────────


def _fade(widget: QWidget, start: float, end: float, ms: int) -> QPropertyAnimation:
    anim = QPropertyAnimation(widget.graphicsEffect(), b"opacity")
    anim.setDuration(ms)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.InOutQuad)
    return anim


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────


def main():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

    app = QApplication(sys.argv)
    icon = QIcon(asset_path("icons", "logo.png"))
    app.setWindowIcon(icon)

    sound = QSoundEffect()
    sound.setSource(QUrl.fromLocalFile(asset_path("audio", "startup.wav")))
    sound.setVolume(0.5)

    splash = SplashScreen()
    splash.show()
    sound.play()
    app.processEvents()

    fade_in = _fade(splash, 0.0, 1.0, 180)
    fade_out = _fade(splash, 1.0, 0.0, 180)
    fade_in.start()

    window = MainWindow()
    window.setWindowIcon(icon)

    QTimer.singleShot(900, fade_out.start)
    QTimer.singleShot(1100, lambda: (splash.close(), window.showMaximized()))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

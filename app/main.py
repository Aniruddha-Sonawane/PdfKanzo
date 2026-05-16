import ctypes
import os
import sys

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)

from PySide6.QtGui import (
    QGuiApplication,
    QIcon,
    QPixmap,
)

from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QLabel,
    QWidget,
)

from ui.main_window import MainWindow

APP_ID = "PdfKanzo.Desktop.App"


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset_path(*paths):

    return os.path.join(BASE_DIR, "assets", *paths)


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

        self.center_on_screen()

        self.opacity_effect = QGraphicsOpacityEffect()

        self.setGraphicsEffect(self.opacity_effect)

    def center_on_screen(self):

        screen = QGuiApplication.primaryScreen()

        geometry = screen.availableGeometry()

        x = (geometry.width() - self.width()) // 2

        y = (geometry.height() - self.height()) // 2

        self.move(x, y)


def fade_animation(widget, start, end, duration):

    animation = QPropertyAnimation(widget.graphicsEffect(), b"opacity")

    animation.setDuration(duration)

    animation.setStartValue(start)
    animation.setEndValue(end)

    animation.setEasingCurve(QEasingCurve.InOutQuad)

    return animation


def main():

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

    app = QApplication(sys.argv)

    icon = QIcon(asset_path("icons", "logo.png"))

    app.setWindowIcon(icon)

    splash = SplashScreen()

    splash.show()

    app.processEvents()

    fade_in = fade_animation(splash, 0.0, 1.0, 180)

    fade_out = fade_animation(splash, 1.0, 0.0, 180)

    fade_in.start()

    window = MainWindow()

    window.setWindowIcon(icon)

    def start_fade_out():

        fade_out.start()

    def show_main_window():

        splash.close()

        window.showMaximized()

    QTimer.singleShot(900, start_fade_out)

    QTimer.singleShot(1100, show_main_window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

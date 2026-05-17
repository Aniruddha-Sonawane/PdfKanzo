import fitz

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Background render thread
# ─────────────────────────────────────────────────────────────────────────────


class _RenderThread(QThread):

    page_rendered = Signal(int, QPixmap)
    render_done = Signal()

    def __init__(self, path: str):
        super().__init__()
        self._path = path
        self._abort = False

    def stop(self):
        self._abort = True

    def run(self):
        try:
            doc = fitz.open(self._path)
            for n in range(len(doc)):
                if self._abort:
                    break
                page = doc.load_page(n)
                pix = page.get_pixmap(matrix=fitz.Matrix(0.45, 0.45))
                img = QImage(
                    pix.samples,
                    pix.width,
                    pix.height,
                    pix.stride,
                    QImage.Format_RGB888,
                )
                pixmap = QPixmap.fromImage(img).scaledToWidth(
                    320, Qt.SmoothTransformation
                )
                self.page_rendered.emit(n, pixmap)
        except Exception:
            pass
        finally:
            self.render_done.emit()


# ─────────────────────────────────────────────────────────────────────────────
#  PDF viewer panel
# ─────────────────────────────────────────────────────────────────────────────


class PdfViewer(QWidget):

    def __init__(self):
        super().__init__()
        self._thread: _RenderThread | None = None
        self._loading_label: QLabel | None = None
        self._setup_ui()

    # ── UI setup ─────────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("PDF Preview")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 22px; font-weight: bold; padding: 10px; color: white;"
        )
        layout.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border: none; background: #1e1e1e;")

        self._container = QWidget()
        self._clayout = QVBoxLayout(self._container)
        self._clayout.setAlignment(Qt.AlignTop)
        self._clayout.setSpacing(12)
        self._clayout.setContentsMargins(8, 8, 8, 8)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

    # ── Public API ────────────────────────────────────────────────────────────

    def load_pdf(self, path: str):
        self._stop_thread()
        self._clear()

        # Show loading indicator
        self._loading_label = QLabel("⏳  Loading preview…")
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._loading_label.setStyleSheet(
            "color: #888; font-size: 15px; padding: 50px;"
        )
        self._clayout.addWidget(self._loading_label)

        self._thread = _RenderThread(path)
        self._thread.page_rendered.connect(self._add_page)
        self._thread.render_done.connect(self._on_done)
        self._thread.start()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.quit()
            self._thread.wait(600)

    def _clear(self):
        while self._clayout.count():
            item = self._clayout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._loading_label = None

    def _remove_loading(self):
        if self._loading_label:
            self._loading_label.deleteLater()
            self._loading_label = None

    def _add_page(self, n: int, pixmap: QPixmap):
        self._remove_loading()

        page_w = QWidget()
        page_l = QVBoxLayout(page_w)
        page_l.setContentsMargins(4, 2, 4, 6)
        page_l.setSpacing(4)

        cb = QCheckBox(f"Page {n + 1}")
        cb.setChecked(True)
        cb.setStyleSheet("color: white; font-size: 13px; padding: 2px;")

        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setPixmap(pixmap)
        lbl.setStyleSheet("background: white; padding: 8px; border-radius: 8px;")

        page_l.addWidget(cb)
        page_l.addWidget(lbl)
        self._clayout.addWidget(page_w)

    def _on_done(self):
        self._remove_loading()

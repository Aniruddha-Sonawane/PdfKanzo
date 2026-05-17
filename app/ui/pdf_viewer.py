import fitz

from PySide6.QtCore import Qt, QThread, Signal, QRectF
from PySide6.QtGui import QImage, QPixmap, QWheelEvent, QTransform
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
    QWidget,
)

_RENDER_SCALE = 2.0  # render at 2× (144 DPI) – stored once, never re-rendered


# ─────────────────────────────────────────────────────────────────────────────
#  Render thread – fires once per PDF load
# ─────────────────────────────────────────────────────────────────────────────


class _RenderThread(QThread):
    page_ready = Signal(int, QPixmap, float, float)  # n, pixmap, pt_w, pt_h
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
            mat = fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE)
            for n in range(len(doc)):
                if self._abort:
                    break
                page = doc.load_page(n)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = QImage(
                    pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888
                )
                self.page_ready.emit(
                    n, QPixmap.fromImage(img), page.rect.width, page.rect.height
                )
        except Exception as e:
            print(f"[PdfViewer] {e}")
        finally:
            self.render_done.emit()


# ─────────────────────────────────────────────────────────────────────────────
#  QGraphicsView – zoom via transform, NO pixmap scaling ever
# ─────────────────────────────────────────────────────────────────────────────


class _PdfGraphicsView(QGraphicsView):
    """
    Zoom works by calling self.scale() which changes the view transform.
    Qt re-draws the scene using the GPU-accelerated painter – instant at any
    zoom level regardless of how many pages are loaded.
    """

    _MIN_ZOOM = 0.10
    _MAX_ZOOM = 8.0

    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self._zoom_level = 1.0

        self.setRenderHint(self.renderHints().Antialiasing, True)
        self.setRenderHint(self.renderHints().SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(Qt.black)  # will be overridden by stylesheet
        self.setStyleSheet("background: #2b2b2b; border: none;")

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            new_z = max(self._MIN_ZOOM, min(self._MAX_ZOOM, self._zoom_level * factor))
            if abs(new_z - self._zoom_level) > 1e-4:
                ratio = new_z / self._zoom_level
                self._zoom_level = new_z
                self.scale(ratio, ratio)  # ← the entire secret: ONE call, instant
            event.accept()
        else:
            # normal scroll: just scroll vertically
            super().wheelEvent(event)

    def zoom_level(self) -> float:
        return self._zoom_level

    def reset_zoom(self):
        self.setTransform(QTransform())
        self._zoom_level = 1.0


# ─────────────────────────────────────────────────────────────────────────────
#  PdfViewer widget
# ─────────────────────────────────────────────────────────────────────────────

_PAGE_GAP = 16  # vertical gap between pages in scene units
_PAGE_SCALE = 1.0 / _RENDER_SCALE  # display pixmap at 1:1 PDF points


class PdfViewer(QWidget):

    def __init__(self):
        super().__init__()
        self._thread: _RenderThread | None = None
        self._path: str | None = None
        self._y_cursor = 0.0  # where to place the next page in the scene

        self._setup_ui()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = QLabel("PDF Preview")
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 8px;"
            "color: #aaa; background: #1a1a1a; border-bottom: 1px solid #333;"
        )
        root.addWidget(hdr)

        self._zoom_label = QLabel("Ctrl + Scroll  ·  zoom in/out")
        self._zoom_label.setAlignment(Qt.AlignCenter)
        self._zoom_label.setStyleSheet(
            "color: #555; font-size: 11px; padding: 3px; background: #1a1a1a;"
        )
        root.addWidget(self._zoom_label)

        self._scene = QGraphicsScene()
        self._view = _PdfGraphicsView(self._scene)
        root.addWidget(self._view)

    # ── Public ───────────────────────────────────────────────────────────────

    def load_pdf(self, path: str):
        self._path = path
        self._stop_thread()
        self._scene.clear()
        self._y_cursor = 0.0
        self._view.reset_zoom()
        self._zoom_label.setText("Ctrl + Scroll  ·  zoom in/out")

        # Loading placeholder text in scene
        self._loading_item = self._scene.addText("⏳  Loading preview…")
        self._loading_item.setDefaultTextColor(Qt.gray)

        self._thread = _RenderThread(path)
        self._thread.page_ready.connect(self._on_page_ready)
        self._thread.render_done.connect(self._on_render_done)
        self._thread.start()

    # ── Thread callbacks ──────────────────────────────────────────────────────

    def _on_page_ready(self, n: int, pixmap: QPixmap, pt_w: float, pt_h: float):
        # Remove loading placeholder on first page
        if hasattr(self, "_loading_item") and self._loading_item:
            self._scene.removeItem(self._loading_item)
            self._loading_item = None

        # Scale the pixmap item so it displays at PDF-point size (1pt = 1px at 100%)
        item = QGraphicsPixmapItem(pixmap)
        item.setTransformationMode(Qt.SmoothTransformation)  # GPU smooth, zero cost
        item.setScale(_PAGE_SCALE)  # scale item, not pixmap

        # White background shadow rect
        bg = self._scene.addRect(
            QRectF(0, self._y_cursor, pt_w, pt_h),
            pen=Qt.NoPen,
        )
        bg.setBrush(Qt.white)

        item.setPos(0, self._y_cursor)
        self._scene.addItem(item)

        self._y_cursor += pt_h + _PAGE_GAP

        # Update zoom label with percentage
        pct = int(self._view.zoom_level() * 100)
        self._zoom_label.setText(f"Ctrl + Scroll to zoom  ·  {pct}%")

    def _on_render_done(self):
        if hasattr(self, "_loading_item") and self._loading_item:
            self._scene.removeItem(self._loading_item)
            self._loading_item = None

    # ── Internals ─────────────────────────────────────────────────────────────

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.quit()
            self._thread.wait(800)
        self._thread = None

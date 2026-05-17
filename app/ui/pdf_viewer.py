import fitz

from PySide6.QtCore import Qt, QThread, Signal, QRectF
from PySide6.QtGui import QImage, QPixmap, QTransform, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
    QWidget,
)

_RENDER_SCALE = 2.0  # render at 2× (144 DPI)
_PAGE_SCALE = 1.0 / _RENDER_SCALE
_PAGE_GAP = 16


# ─────────────────────────────────────────────────────────────────────────────
#  Render thread
# ─────────────────────────────────────────────────────────────────────────────


class _RenderThread(QThread):
    page_ready = Signal(int, QPixmap, float, float)
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
#  Graphics view with Ctrl+Scroll zoom
# ─────────────────────────────────────────────────────────────────────────────


class _PdfGraphicsView(QGraphicsView):
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
        self.setStyleSheet("background: #2b2b2b; border: none;")

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            new_z = max(self._MIN_ZOOM, min(self._MAX_ZOOM, self._zoom_level * factor))
            if abs(new_z - self._zoom_level) > 1e-4:
                ratio = new_z / self._zoom_level
                self._zoom_level = new_z
                self.scale(ratio, ratio)
            event.accept()
        else:
            super().wheelEvent(event)

    def reset_zoom(self):
        self.setTransform(QTransform())
        self._zoom_level = 1.0


# ─────────────────────────────────────────────────────────────────────────────
#  PdfViewer  –  caches every scene by path, never re-renders on re-click
# ─────────────────────────────────────────────────────────────────────────────


class PdfViewer(QWidget):
    """
    _scene_cache: dict[path -> QGraphicsScene]
      Rendered once, swapped instantly on re-click. No re-render ever.
    _thread_cache: dict[path -> bool]
      Tracks which paths are fully rendered (True) or still loading (False).
    """

    def __init__(self):
        super().__init__()
        self._thread: _RenderThread | None = None
        self._current_path: str | None = None
        self._loading_path: str | None = None  # path being rendered right now

        # path → QGraphicsScene (fully or partially built)
        self._scene_cache: dict[str, QGraphicsScene] = {}
        # path → y cursor (where next page goes in that scene)
        self._y_cache: dict[str, float] = {}
        # path → loading text item (removed when first page arrives)
        self._loading_item: dict[str, object] = {}

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

        # Single shared scene + view; we swap the scene when switching PDFs
        self._scene = QGraphicsScene()
        self._view = _PdfGraphicsView(self._scene)
        root.addWidget(self._view)

    # ── Public ───────────────────────────────────────────────────────────────

    def load_pdf(self, path: str):
        """
        If this path was already rendered (or is being rendered), just swap
        the scene instantly — no thread, no delay.
        If it's new, start a render thread and cache the scene as pages arrive.
        """
        if path == self._current_path:
            return  # already showing this PDF

        self._current_path = path

        if path in self._scene_cache:
            # ── Cache hit: swap scene instantly ──────────────────────────────
            self._view.setScene(self._scene_cache[path])
            self._view.reset_zoom()
            return

        # ── Cache miss: build a new scene and start rendering ────────────────
        scene = QGraphicsScene()
        self._scene_cache[path] = scene
        self._y_cache[path] = 0.0

        loading = scene.addText("⏳  Loading preview…")
        loading.setDefaultTextColor(Qt.gray)
        self._loading_item[path] = loading

        self._view.setScene(scene)
        self._view.reset_zoom()

        # Stop any in-flight render for a different path
        self._stop_thread()

        self._loading_path = path
        self._thread = _RenderThread(path)
        self._thread.page_ready.connect(self._on_page_ready)
        self._thread.render_done.connect(self._on_render_done)
        self._thread.start()

    # ── Thread callbacks ──────────────────────────────────────────────────────

    def _on_page_ready(self, n: int, pixmap: QPixmap, pt_w: float, pt_h: float):
        path = self._loading_path
        if path not in self._scene_cache:
            return
        scene = self._scene_cache[path]

        # Remove loading placeholder on first page
        li = self._loading_item.pop(path, None)
        if li:
            scene.removeItem(li)

        y = self._y_cache.get(path, 0.0)

        # White page background
        bg = scene.addRect(QRectF(0, y, pt_w, pt_h), pen=Qt.NoPen)
        bg.setBrush(Qt.white)

        # Page pixmap item – scaled via item transform, not pixel copy
        item = QGraphicsPixmapItem(pixmap)
        item.setTransformationMode(Qt.SmoothTransformation)
        item.setScale(_PAGE_SCALE)
        item.setPos(0, y)
        scene.addItem(item)

        # Page number label below the page
        num_item = scene.addText(f"— {n + 1} —")
        num_item.setDefaultTextColor(Qt.gray)
        num_item.setPos(pt_w / 2 - num_item.boundingRect().width() / 2, y + pt_h + 2)

        self._y_cache[path] = y + pt_h + _PAGE_GAP

    def _on_render_done(self):
        path = self._loading_path
        li = self._loading_item.pop(path, None)
        if li and path in self._scene_cache:
            self._scene_cache[path].removeItem(li)
        self._loading_path = None

    # ── Internals ─────────────────────────────────────────────────────────────

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.quit()
            self._thread.wait(800)
        self._thread = None

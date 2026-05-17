import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from pypdf import PdfReader

from core.pdf_merger import merge_files
from ui.file_table import FileTable
from ui.pdf_viewer import PdfViewer


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PdfKanzo")
        self._setup_ui()
        self._apply_styles()

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel – PDF viewer
        self.viewer = PdfViewer()
        splitter.addWidget(self.viewer)

        # Right panel – file list + controls
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 8, 8)
        right_layout.setSpacing(8)

        title = QLabel("PdfKanzo")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold; padding: 15px; color: white;"
        )
        right_layout.addWidget(title)

        self.table = FileTable()
        self.table.selection_changed.connect(self._on_selection_changed)
        right_layout.addWidget(self.table)

        bottom = QHBoxLayout()
        self.output_name = QLineEdit()
        self.output_name.setPlaceholderText("Output PDF Name")
        merge_btn = QPushButton("Merge PDF")
        merge_btn.clicked.connect(self._merge_pdf)
        bottom.addWidget(self.output_name)
        bottom.addWidget(merge_btn)
        right_layout.addLayout(bottom)

        splitter.addWidget(right)
        splitter.setSizes([700, 700])

        self._create_toolbar()

    def _create_toolbar(self):
        tb = QToolBar()
        self.addToolBar(tb)
        for label, slot in [
            ("Add PDF", self._add_pdf),
            ("Add Image", self._add_image),
            ("Remove", self._remove_selected),  # ← renamed
        ]:
            action = QAction(label, self)
            action.triggered.connect(slot)
            tb.addAction(action)

    # ── Stylesheet ────────────────────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: #1e1e1e;
            }

            QWidget {
                background: #1e1e1e;
            }

            QLabel {
                color: white;
                background: transparent;
            }

            /* ── Table ── */
            QTableWidget {
                background: #2a2a2a;
                color: white;
                gridline-color: #3a3a3a;
                border: none;
                font-size: 14px;
                outline: 0;
            }
            QTableWidget::item {
                padding: 6px 10px;
            }
            QTableWidget::item:selected {
                background: #3a3a5c;
                color: white;
            }
            QTableWidget::item:focus {
                background: #3a3a5c;
                outline: none;
                border: none;
            }
            QHeaderView::section {
                background: #333;
                color: white;
                padding: 8px 10px;
                border: none;
                font-size: 13px;
            }

            /* ── Buttons ── */
            QPushButton {
                background: #3a86ff;
                color: white;
                border: none;
                padding: 10px 18px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #5396ff;
            }

            /* ── Line edits (output name field) ── */
            QLineEdit {
                padding: 10px;
                border-radius: 8px;
                background: #2a2a2a;
                color: white;
                border: 1px solid #444;
                font-size: 14px;
            }

            /* ── Toolbar ── */
            QToolBar {
                background: #242424;
                border-bottom: 1px solid #333;
                padding: 4px 6px;
                spacing: 4px;
            }
            QToolButton {
                color: white;
                background: #333;
                border: none;
                padding: 6px 14px;
                border-radius: 6px;
                font-size: 13px;
            }
            QToolButton:hover {
                background: #444;
            }

            /* ── Checkboxes (in viewer) ── */
            QCheckBox {
                color: white;
                font-size: 13px;
                padding: 3px;
                background: transparent;
            }

            /* ── Scrollbars ── */
            QScrollBar:vertical {
                background: #242424;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollArea {
                border: none;
                background: #1e1e1e;
            }

            /* ── Splitter ── */
            QSplitter::handle {
                background: #333;
                width: 1px;
            }
        """)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_selection_changed(self):
        data = self.table.get_current_row_data()
        if data and data["type"] == "PDF":
            self.viewer.load_pdf(data["path"])

    def _add_pdf(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDFs", "", "PDF Files (*.pdf)"
        )
        for f in files:
            reader = PdfReader(f)
            self.table.add_file(f, "PDF", len(reader.pages))

    def _add_image(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)",
        )
        for f in files:
            self.table.add_file(f, "IMG", 1)

    def _remove_selected(self):
        """Remove the currently selected row."""
        self.table.remove_selected()

    def _merge_pdf(self):
        rows = self.table.get_all_rows()
        if not rows:
            QMessageBox.warning(self, "Error", "No files added")
            return

        name = self.output_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Enter an output file name")
            return
        if not name.endswith(".pdf"):
            name += ".pdf"

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        out_path = os.path.join(desktop, name)

        try:
            merge_files(rows, out_path)
            QMessageBox.information(self, "Success", f"Saved to:\n{out_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Merge Error", str(exc))

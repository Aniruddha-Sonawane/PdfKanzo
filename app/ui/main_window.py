import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
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

        # ── Left panel: PDF viewer ────────────────────────────────────────────
        self.viewer = PdfViewer()
        splitter.addWidget(self.viewer)

        # ── Right panel ───────────────────────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        # Title
        title = QLabel("PdfKanzo")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold; padding: 10px 0 6px 0; color: white;"
        )
        right_layout.addWidget(title)

        # ── Button row: Add PDF | Add Image | Remove  (above the table) ───────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_add_pdf = QPushButton("＋ Add PDF")
        self._btn_add_image = QPushButton("＋ Add Image")
        self._btn_remove = QPushButton("✕ Remove")
        self._btn_remove.setObjectName("removeBtn")

        for btn in (self._btn_add_pdf, self._btn_add_image, self._btn_remove):
            btn.setFixedHeight(36)
            btn_row.addWidget(btn)

        self._btn_add_pdf.clicked.connect(self._add_pdf)
        self._btn_add_image.clicked.connect(self._add_image)
        self._btn_remove.clicked.connect(self._remove_selected)

        right_layout.addLayout(btn_row)

        # ── File table ────────────────────────────────────────────────────────
        self.table = FileTable()
        self.table.selection_changed.connect(self._on_selection_changed)
        right_layout.addWidget(self.table)

        # ── Bottom row: output name + merge ───────────────────────────────────
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

    # ── Stylesheet ────────────────────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
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
            QTableWidget::item { padding: 6px 10px; }
            QTableWidget::item:selected { background: #3a3a5c; color: white; }
            QTableWidget::item:focus    { background: #3a3a5c; outline: none; border: none; }
            QHeaderView::section {
                background: #333; color: white;
                padding: 8px 10px; border: none; font-size: 13px;
            }

            /* ── Buttons (default blue) ── */
            QPushButton {
                background: #3a86ff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover { background: #5396ff; }

            /* Remove button – red tint */
            QPushButton#removeBtn {
                background: #c0392b;
            }
            QPushButton#removeBtn:hover {
                background: #e74c3c;
            }

            /* ── Line edit ── */
            QLineEdit {
                padding: 10px;
                border-radius: 8px;
                background: #2a2a2a;
                color: white;
                border: 1px solid #444;
                font-size: 14px;
            }

            /* ── Scrollbars ── */
            QScrollBar:vertical {
                background: #242424; width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #555; border-radius: 4px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollArea { border: none; background: #1e1e1e; }

            /* ── Splitter ── */
            QSplitter::handle { background: #333; width: 1px; }
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

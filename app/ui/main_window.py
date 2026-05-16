import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pypdf import PdfReader

from core.pdf_merger import merge_files


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.rows = []

        self.setWindowTitle("PdfKanzo")

        self.setup_ui()

    def setup_ui(self):

        central_widget = QWidget()

        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        central_widget.setLayout(layout)

        title = QLabel("PdfKanzo")

        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            padding: 15px;
        """)

        layout.addWidget(title)

        self.table = QTableWidget()

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels(
            ["File", "Type", "Pages", "Page Selection"]
        )

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()

        self.output_name = QLineEdit()

        self.output_name.setPlaceholderText("Output PDF Name")

        merge_button = QPushButton("Merge PDF")

        merge_button.clicked.connect(self.merge_pdf)

        bottom_layout.addWidget(self.output_name)

        bottom_layout.addWidget(merge_button)

        layout.addLayout(bottom_layout)

        self.create_toolbar()

        self.setStyleSheet("""
            QMainWindow {
                background: #1e1e1e;
            }

            QLabel {
                color: white;
            }

            QTableWidget {
                background: #2a2a2a;
                color: white;
                gridline-color: #444;
                border: none;
                font-size: 14px;
            }

            QHeaderView::section {
                background: #333;
                color: white;
                padding: 8px;
                border: none;
            }

            QPushButton {
                background: #3a86ff;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
            }

            QPushButton:hover {
                background: #5396ff;
            }

            QLineEdit {
                padding: 10px;
                border-radius: 8px;
                background: #2a2a2a;
                color: white;
                border: 1px solid #444;
            }
        """)

    def create_toolbar(self):

        toolbar = QToolBar()

        self.addToolBar(toolbar)

        add_pdf_action = QAction("Add PDF", self)

        add_image_action = QAction("Add Image", self)

        remove_action = QAction("Remove Last", self)

        add_pdf_action.triggered.connect(self.add_pdf)

        add_image_action.triggered.connect(self.add_image)

        remove_action.triggered.connect(self.remove_last)

        toolbar.addAction(add_pdf_action)

        toolbar.addAction(add_image_action)

        toolbar.addAction(remove_action)

    def add_pdf(self):

        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDFs", "", "PDF Files (*.pdf)"
        )

        if not files:
            return

        for file in files:

            reader = PdfReader(file)

            total = len(reader.pages)

            self.add_row(file, "PDF", total)

    def add_image(self):

        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)"
        )

        if not files:
            return

        for file in files:

            self.add_row(file, "IMG", 1)

    def add_row(self, path, file_type, total_pages):

        row = self.table.rowCount()

        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(path)))

        self.table.setItem(row, 1, QTableWidgetItem(file_type))

        self.table.setItem(row, 2, QTableWidgetItem(str(total_pages)))

        page_input = QLineEdit()

        if file_type == "IMG":

            page_input.setText("1")
            page_input.setDisabled(True)

        else:

            page_input.setText(f"1-{total_pages}")

        self.table.setCellWidget(row, 3, page_input)

        self.rows.append(
            {
                "path": path,
                "type": file_type,
                "pages": page_input.text(),
            }
        )

    def remove_last(self):

        row_count = self.table.rowCount()

        if row_count == 0:
            return

        self.table.removeRow(row_count - 1)

        self.rows.pop()

    def merge_pdf(self):

        if not self.rows:

            QMessageBox.warning(self, "Error", "No files added")

            return

        output_name = self.output_name.text().strip()

        if not output_name:

            QMessageBox.warning(self, "Error", "Enter output name")

            return

        if not output_name.endswith(".pdf"):

            output_name += ".pdf"

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")

        output_path = os.path.join(desktop, output_name)

        updated_rows = []

        for index, row in enumerate(self.rows):

            page_widget = self.table.cellWidget(index, 3)

            updated_rows.append(
                {"path": row["path"], "type": row["type"], "pages": page_widget.text()}
            )

        try:

            merge_files(updated_rows, output_path)

            QMessageBox.information(self, "Success", f"Saved to:\n{output_path}")

        except Exception as e:

            QMessageBox.critical(self, "Error", str(e))

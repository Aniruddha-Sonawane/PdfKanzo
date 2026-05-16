from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.pdf_merger import merge_pdfs


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PdfKanzo")
        self.resize(1000, 700)

        self.pdf_files = []

        self.setup_ui()

    def setup_ui(self):

        central_widget = QWidget()

        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        title = QLabel("PdfKanzo")
        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            padding: 20px;
        """)

        main_layout.addWidget(title)

        self.file_list = QListWidget()

        main_layout.addWidget(self.file_list)

        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add PDFs")
        self.merge_button = QPushButton("Merge PDFs")

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.merge_button)

        main_layout.addLayout(button_layout)

        self.add_button.clicked.connect(self.add_pdfs)

        self.merge_button.clicked.connect(self.merge_files)

    def add_pdfs(self):

        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDFs", "", "PDF Files (*.pdf)"
        )

        if not files:
            return

        for file in files:

            self.pdf_files.append(file)

            self.file_list.addItem(file)

    def merge_files(self):

        if len(self.pdf_files) < 2:

            QMessageBox.warning(self, "Warning", "Add at least 2 PDFs")

            return

        output_file, _ = QFileDialog.getSaveFileName(
            self, "Save Merged PDF", "merged.pdf", "PDF Files (*.pdf)"
        )

        if not output_file:
            return

        try:

            merge_pdfs(self.pdf_files, output_file)

            QMessageBox.information(self, "Success", "PDF merged successfully")

        except Exception as e:

            QMessageBox.critical(self, "Error", str(e))

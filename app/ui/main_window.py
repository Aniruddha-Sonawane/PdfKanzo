import os

import fitz

from PySide6.QtCore import Qt

from PySide6.QtGui import (
    QAction,
    QImage,
    QPixmap,
)

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
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

        main_layout = QHBoxLayout()

        central_widget.setLayout(main_layout)

        splitter = QSplitter(Qt.Horizontal)

        main_layout.addWidget(splitter)

        #
        # LEFT SIDE — PDF VIEWER
        #

        viewer_widget = QWidget()

        viewer_layout = QVBoxLayout()

        viewer_widget.setLayout(viewer_layout)

        viewer_title = QLabel("PDF Preview")

        viewer_title.setAlignment(Qt.AlignCenter)

        viewer_title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            padding: 10px;
            color: white;
        """)

        viewer_layout.addWidget(viewer_title)

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(True)

        self.scroll_area.setStyleSheet("""
            border: none;
            background: #1e1e1e;
        """)

        self.preview_container = QWidget()

        self.preview_layout = QVBoxLayout()

        self.preview_layout.setAlignment(Qt.AlignTop)

        self.preview_container.setLayout(self.preview_layout)

        self.scroll_area.setWidget(self.preview_container)

        viewer_layout.addWidget(self.scroll_area)

        #
        # RIGHT SIDE — CONTROLS
        #

        right_widget = QWidget()

        layout = QVBoxLayout()

        right_widget.setLayout(layout)

        title = QLabel("PdfKanzo")

        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            padding: 15px;
            color: white;
        """)

        layout.addWidget(title)

        self.table = QTableWidget()

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels(
            ["File", "Type", "Pages", "Page Selection"]
        )

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        self.table.selectionModel().selectionChanged.connect(self.preview_selected_pdf)

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

        splitter.addWidget(viewer_widget)

        splitter.addWidget(right_widget)

        splitter.setSizes([700, 700])

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

            QCheckBox {
                color: white;
                font-size: 14px;
                padding: 5px;
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

    def preview_selected_pdf(self):

        selected = self.table.currentRow()

        if selected < 0:
            return

        row = self.rows[selected]

        if row["type"] != "PDF":
            return

        pdf_path = row["path"]

        try:

            #
            # CLEAR OLD PREVIEW
            #

            while self.preview_layout.count():

                item = self.preview_layout.takeAt(0)

                widget = item.widget()

                if widget:
                    widget.deleteLater()

            #
            # OPEN PDF
            #

            doc = fitz.open(pdf_path)

            #
            # RENDER ALL PAGES
            #

            for page_number in range(len(doc)):

                page = doc.load_page(page_number)

                #
                # LOWER RESOLUTION RENDER
                #

                pix = page.get_pixmap(matrix=fitz.Matrix(0.45, 0.45))

                image = QImage(
                    pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888
                )

                pixmap = QPixmap.fromImage(image)

                #
                # SMALLER PREVIEW WIDTH
                #

                scaled_pixmap = pixmap.scaledToWidth(320, Qt.SmoothTransformation)

                #
                # PAGE CONTAINER
                #

                page_widget = QWidget()

                page_layout = QVBoxLayout()

                page_widget.setLayout(page_layout)

                #
                # PAGE CHECKBOX
                #

                checkbox = QCheckBox(f"Page {page_number + 1}")

                checkbox.setChecked(True)

                #
                # PAGE IMAGE
                #

                label = QLabel()

                label.setAlignment(Qt.AlignCenter)

                label.setPixmap(scaled_pixmap)

                label.setStyleSheet("""
                    background: white;
                    padding: 10px;
                    border-radius: 10px;
                """)

                #
                # ADD TO LAYOUT
                #

                page_layout.addWidget(checkbox)

                page_layout.addWidget(label)

                self.preview_layout.addWidget(page_widget)

        except Exception as e:

            QMessageBox.critical(self, "Preview Error", str(e))

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

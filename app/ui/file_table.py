import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

_PAGE_INPUT_STYLE = """
    QLineEdit {
        background: transparent;
        color: white;
        border: none;
        padding: 2px 8px;
        font-size: 14px;
    }
    QLineEdit:focus {
        border-bottom: 1px solid #3a86ff;
    }
    QLineEdit:disabled {
        color: #666;
    }
"""

_BTN_STYLE = """
    QPushButton {
        background: #333;
        color: white;
        border: none;
        border-radius: 4px;
        font-size: 14px;
        padding: 0px;
        min-width: 24px;
        max-width: 24px;
        min-height: 20px;
        max-height: 20px;
    }
    QPushButton:hover { background: #555; }
    QPushButton:pressed { background: #3a86ff; }
"""


class _NoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option: QStyleOptionViewItem, index):
        opt = QStyleOptionViewItem(option)
        opt.state &= ~opt.state.State_HasFocus  # type: ignore[attr-defined]
        super().paint(painter, opt, index)


class FileTable(QTableWidget):
    """
    Columns: [▲▼ buttons] [File] [Type] [Pages] [Page Selection]
    No drag-drop. Up/down buttons move the selected row.
    """

    selection_changed = Signal()

    # col indices
    COL_BTNS = 0
    COL_FILE = 1
    COL_TYPE = 2
    COL_PAGES = 3
    COL_SEL = 4

    def __init__(self):
        super().__init__()
        self._rows: list[dict] = []  # [{path, type, total_pages}]
        self._setup()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup(self):
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["", "File", "Type", "Pages", "Page Selection"])

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(self.COL_BTNS, QHeaderView.Fixed)
        hh.setSectionResizeMode(self.COL_FILE, QHeaderView.Stretch)
        hh.setSectionResizeMode(self.COL_TYPE, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(self.COL_PAGES, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(self.COL_SEL, QHeaderView.ResizeToContents)
        self.setColumnWidth(self.COL_BTNS, 58)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(46)

        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setItemDelegate(_NoFocusDelegate(self))
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)

        self.selectionModel().selectionChanged.connect(self.selection_changed)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_file(self, path: str, file_type: str, total_pages: int):
        default = "1" if file_type == "IMG" else f"1-{total_pages}"
        idx = self.rowCount()
        self._rows.append({"path": path, "type": file_type, "total_pages": total_pages})
        self._build_row(idx, path, file_type, total_pages, default)
        self._refresh_buttons()
        self._rebind_all()

    def remove_selected(self):
        row = self.currentRow()
        if row < 0 or row >= self.rowCount():
            return
        self.removeRow(row)
        if 0 <= row < len(self._rows):
            self._rows.pop(row)
        new_count = self.rowCount()
        if new_count > 0:
            self.selectRow(min(row, new_count - 1))
        self._refresh_buttons()
        self._rebind_all()

    def remove_last(self):
        self.remove_selected()

    def get_current_row_data(self) -> dict | None:
        row = self.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def get_all_rows(self) -> list[dict]:
        result = []
        for i in range(self.rowCount()):
            rd = self._rows[i].copy() if i < len(self._rows) else {}
            w = self.cellWidget(i, self.COL_SEL)
            rd["pages"] = w.text() if w else ""
            result.append(rd)
        return result

    # ── Row building ──────────────────────────────────────────────────────────

    def _build_row(
        self,
        idx: int,
        path: str,
        file_type: str,
        total_pages: int,
        page_text: str,
        disabled: bool | None = None,
    ):
        self.insertRow(idx)

        # col 0: up/down buttons widget (rebuilt by _refresh_buttons)
        placeholder = QTableWidgetItem("")
        placeholder.setFlags(Qt.NoItemFlags)
        self.setItem(idx, self.COL_BTNS, placeholder)

        # cols 1-3: static text
        for col, text in zip(
            [self.COL_FILE, self.COL_TYPE, self.COL_PAGES],
            [os.path.basename(path), file_type, str(total_pages)],
        ):
            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.setItem(idx, col, item)

        # col 4: editable page selection
        le = QLineEdit()
        le.setText(page_text)
        le.setStyleSheet(_PAGE_INPUT_STYLE)
        if disabled is None:
            disabled = file_type == "IMG"
        le.setDisabled(disabled)
        self.setCellWidget(idx, self.COL_SEL, le)

    def _make_btn_widget(self, row: int) -> QWidget:
        """Return a widget with ▲ and ▼ buttons for the given row."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        up_btn = QPushButton("▲")
        dn_btn = QPushButton("▼")
        up_btn.setStyleSheet(_BTN_STYLE)
        dn_btn.setStyleSheet(_BTN_STYLE)
        up_btn.setToolTip("Move up")
        dn_btn.setToolTip("Move down")

        up_btn.clicked.connect(lambda _, r=row: self._move_row(r, r - 1))
        dn_btn.clicked.connect(lambda _, r=row: self._move_row(r, r + 1))

        lay.addWidget(up_btn)
        lay.addWidget(dn_btn)
        return w

    def _refresh_buttons(self):
        """Rebuild all ▲▼ button widgets so row indices stay correct."""
        for i in range(self.rowCount()):
            self.setCellWidget(i, self.COL_BTNS, self._make_btn_widget(i))

    def _rebind_all(self):
        for i in range(self.rowCount()):
            w = self.cellWidget(i, self.COL_SEL)
            if isinstance(w, QLineEdit):
                try:
                    w.returnPressed.disconnect()
                except RuntimeError:
                    pass
                w.returnPressed.connect(lambda row=i: self._on_enter(row))

    # ── Enter → new row for same file ────────────────────────────────────────

    def _on_enter(self, _hint: int):
        sender = self.sender()
        actual = -1
        for i in range(self.rowCount()):
            if self.cellWidget(i, self.COL_SEL) is sender:
                actual = i
                break
        if actual < 0 or actual >= len(self._rows):
            return

        src = self._rows[actual]
        new_idx = actual + 1
        self._rows.insert(
            new_idx,
            {
                "path": src["path"],
                "type": src["type"],
                "total_pages": src["total_pages"],
            },
        )
        self._build_row(
            new_idx,
            src["path"],
            src["type"],
            src["total_pages"],
            "",
            disabled=(src["type"] == "IMG"),
        )
        self._refresh_buttons()
        self._rebind_all()

        new_w = self.cellWidget(new_idx, self.COL_SEL)
        if new_w:
            new_w.setFocus()
        self.selectRow(new_idx)

    # ── Move row up / down ────────────────────────────────────────────────────

    def _move_row(self, src: int, dst: int):
        n = self.rowCount()
        if dst < 0 or dst >= n or src < 0 or src >= n or src == dst:
            return

        # Snapshot src
        src_meta = self._rows[src].copy()
        src_cells = [
            (self.item(src, c).text() if self.item(src, c) else "")
            for c in [self.COL_FILE, self.COL_TYPE, self.COL_PAGES]
        ]
        w = self.cellWidget(src, self.COL_SEL)
        src_pages = w.text() if w else ""
        src_disabled = (not w.isEnabled()) if w else False

        # Snapshot dst
        dst_meta = self._rows[dst].copy()
        dst_cells = [
            (self.item(dst, c).text() if self.item(dst, c) else "")
            for c in [self.COL_FILE, self.COL_TYPE, self.COL_PAGES]
        ]
        w2 = self.cellWidget(dst, self.COL_SEL)
        dst_pages = w2.text() if w2 else ""
        dst_disabled = (not w2.isEnabled()) if w2 else False

        # Swap metadata
        self._rows[src], self._rows[dst] = dst_meta, src_meta

        # Swap UI cells for cols 1-3
        for col_idx, col in enumerate([self.COL_FILE, self.COL_TYPE, self.COL_PAGES]):
            self.item(src, col).setText(dst_cells[col_idx])
            self.item(dst, col).setText(src_cells[col_idx])

        # Swap page-selection widgets
        le_src = QLineEdit()
        le_src.setText(dst_pages)
        le_src.setStyleSheet(_PAGE_INPUT_STYLE)
        le_src.setDisabled(dst_disabled)
        self.setCellWidget(src, self.COL_SEL, le_src)

        le_dst = QLineEdit()
        le_dst.setText(src_pages)
        le_dst.setStyleSheet(_PAGE_INPUT_STYLE)
        le_dst.setDisabled(src_disabled)
        self.setCellWidget(dst, self.COL_SEL, le_dst)

        self._refresh_buttons()
        self._rebind_all()
        self.selectRow(dst)

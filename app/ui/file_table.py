import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Delegate that strips the focus rectangle from non-editable cells
# ─────────────────────────────────────────────────────────────────────────────


class _NoFocusDelegate(QStyledItemDelegate):

    def paint(self, painter, option: QStyleOptionViewItem, index):
        opt = QStyleOptionViewItem(option)
        opt.state &= ~opt.state.State_HasFocus  # type: ignore[attr-defined]
        super().paint(painter, opt, index)


# ─────────────────────────────────────────────────────────────────────────────
#  File table widget
# ─────────────────────────────────────────────────────────────────────────────

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


class FileTable(QTableWidget):
    """
    A QTableWidget that:
      • Removes the blue focus cursor from read-only cells (File / Type / Pages).
      • Allows drag-and-drop row reordering (preserving all text).
      • Pressing Enter in a Page Selection cell inserts a NEW ROW below referencing
        the SAME file — no file is added twice; rows are just page-range splits.
      • "Remove" removes the currently selected row (not necessarily the last).
      • Exposes selection_changed signal so MainWindow can react.
    """

    selection_changed = Signal()

    # _rows stores the ground-truth metadata per row: {path, type, total_pages}
    # The QTableWidget rows mirror this list 1-to-1.

    def __init__(self):
        super().__init__()
        self._rows: list[dict] = []
        self._drag_src = -1
        self._setup()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["File", "Type", "Pages", "Page Selection"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setMinimumSectionSize(60)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(46)

        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

        self.setItemDelegate(_NoFocusDelegate(self))

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        self.selectionModel().selectionChanged.connect(self.selection_changed)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_file(self, path: str, file_type: str, total_pages: int):
        """Append a file row to the table."""
        default = "1" if file_type == "IMG" else f"1-{total_pages}"
        idx = self.rowCount()
        self._rows.append({"path": path, "type": file_type, "total_pages": total_pages})
        self._build_row(idx, path, file_type, total_pages, default)
        self._rebind_all()

    def remove_selected(self):
        """Remove whichever row is currently selected."""
        row = self.currentRow()
        if row < 0 or row >= self.rowCount():
            return
        self.removeRow(row)
        if 0 <= row < len(self._rows):
            self._rows.pop(row)
        # Select the next sensible row
        new_count = self.rowCount()
        if new_count > 0:
            self.selectRow(min(row, new_count - 1))
        self._rebind_all()

    # kept for backward compat if anything still calls it
    def remove_last(self):
        self.remove_selected()

    def get_current_row_data(self) -> dict | None:
        row = self.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def get_all_rows(self) -> list[dict]:
        """Return all rows with live page-selection text."""
        result = []
        for i in range(self.rowCount()):
            rd = self._rows[i].copy() if i < len(self._rows) else {}
            w = self.cellWidget(i, 3)
            rd["pages"] = w.text() if w else ""
            result.append(rd)
        return result

    # ── Row building helpers ──────────────────────────────────────────────────

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
        for col, text in enumerate(
            [os.path.basename(path), file_type, str(total_pages)]
        ):
            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.setItem(idx, col, item)

        le = QLineEdit()
        le.setText(page_text)
        le.setStyleSheet(_PAGE_INPUT_STYLE)
        if disabled is None:
            disabled = file_type == "IMG"
        le.setDisabled(disabled)
        self.setCellWidget(idx, 3, le)

    def _rebind_all(self):
        """Re-connect returnPressed for every page-selection widget."""
        for i in range(self.rowCount()):
            w = self.cellWidget(i, 3)
            if isinstance(w, QLineEdit):
                try:
                    w.returnPressed.disconnect()
                except RuntimeError:
                    pass
                w.returnPressed.connect(lambda row=i: self._on_enter(row))

    # ── Enter key → insert a new row for the SAME file below ─────────────────

    def _on_enter(self, _hint: int):
        """
        Find which row the sender lives in.
        Insert a NEW ROW immediately below it referencing the same source file
        but with an empty page-selection field ready for the user to type into.
        No file is "added" again — it is just another page-range segment.
        """
        sender = self.sender()
        actual = -1
        for i in range(self.rowCount()):
            if self.cellWidget(i, 3) is sender:
                actual = i
                break
        if actual < 0 or actual >= len(self._rows):
            return

        src = self._rows[actual]
        new_idx = actual + 1

        # Insert metadata
        self._rows.insert(
            new_idx,
            {
                "path": src["path"],
                "type": src["type"],
                "total_pages": src["total_pages"],
            },
        )

        # Build the UI row
        is_img = src["type"] == "IMG"
        self._build_row(
            new_idx,
            src["path"],
            src["type"],
            src["total_pages"],
            "",
            disabled=is_img,
        )
        self._rebind_all()

        new_w = self.cellWidget(new_idx, 3)
        if new_w:
            new_w.setFocus()
        self.selectRow(new_idx)

    # ── Drag & drop row reordering ────────────────────────────────────────────

    def startDrag(self, actions):
        self._drag_src = self.currentRow()
        super().startDrag(actions)

    def dropEvent(self, event):
        dst = self.indexAt(event.position().toPoint()).row()
        src = self._drag_src

        if dst < 0:
            dst = self.rowCount() - 1
        if src < 0 or src == dst:
            event.ignore()
            return

        # ── Snapshot source row completely ──
        src_meta = self._rows[src].copy()
        src_cells = []
        for c in range(3):
            item = self.item(src, c)
            src_cells.append(item.text() if item else "")
        w = self.cellWidget(src, 3)
        src_pages = w.text() if w else ""
        src_disabled = (not w.isEnabled()) if w else False

        # ── Remove source ──
        self._rows.pop(src)
        self.removeRow(src)

        # ── Adjust destination index after removal ──
        adj = dst if src > dst else dst - 1

        # ── Insert at destination ──
        self._rows.insert(adj, src_meta)
        self.insertRow(adj)
        for col, text in enumerate(src_cells):
            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.setItem(adj, col, item)

        le = QLineEdit()
        le.setText(
            src_pages
        )  # ← this was the bug: text must be set AFTER widget creation
        le.setStyleSheet(_PAGE_INPUT_STYLE)
        le.setDisabled(src_disabled)
        self.setCellWidget(adj, 3, le)

        self._rebind_all()
        self.selectRow(adj)
        event.accept()

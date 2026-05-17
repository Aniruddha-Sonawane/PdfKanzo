import os
import tempfile

from PIL import Image
from pypdf import PdfReader, PdfWriter


def parse_pages(text: str) -> list[int]:
    """
    Convert a page-selection string like "1-3, 5, 7-9" into a flat list of
    1-based page numbers: [1, 2, 3, 5, 7, 8, 9].
    """
    result = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            for i in range(int(start.strip()), int(end.strip()) + 1):
                result.append(i)
        else:
            result.append(int(part))
    return result


def merge_files(rows: list[dict], output_path: str) -> None:
    """
    Merge PDFs and/or images described by *rows* into a single PDF at
    *output_path*.

    Each row dict must contain:
        path  – absolute path to the source file
        type  – "PDF" or "IMG"
        pages – page-selection string (ignored for IMG)
    """
    writer = PdfWriter()
    temp_files = []

    for row in rows:
        if row["type"] == "IMG":
            img = Image.open(row["path"]).convert("RGB")
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_files.append(tmp.name)
            tmp.close()
            img.save(tmp.name)
            reader = PdfReader(tmp.name)
            writer.add_page(reader.pages[0])
        else:
            reader = PdfReader(row["path"])
            pages = parse_pages(row["pages"])
            for p in pages:
                writer.add_page(reader.pages[p - 1])

    with open(output_path, "wb") as fh:
        writer.write(fh)

    for tmp_path in temp_files:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

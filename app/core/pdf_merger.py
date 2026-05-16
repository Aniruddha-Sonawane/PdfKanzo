import os
import tempfile

from PIL import Image
from pypdf import PdfReader, PdfWriter


def parse_pages(text):

    result = []

    for part in text.split(","):

        part = part.strip()

        if "-" in part:

            start, end = part.split("-")

            for i in range(int(start), int(end) + 1):

                result.append(i)

        else:

            result.append(int(part))

    return result


def merge_files(rows, output_path):

    writer = PdfWriter()

    temp_files = []

    for row in rows:

        if row["type"] == "IMG":

            img = Image.open(row["path"]).convert("RGB")

            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

            temp_files.append(tmp.name)

            img.save(tmp.name)

            reader = PdfReader(tmp.name)

            writer.add_page(reader.pages[0])

        else:

            reader = PdfReader(row["path"])

            pages = parse_pages(row["pages"])

            for p in pages:

                writer.add_page(reader.pages[p - 1])

    with open(output_path, "wb") as file:

        writer.write(file)

    for temp in temp_files:

        try:
            os.remove(temp)

        except:
            pass

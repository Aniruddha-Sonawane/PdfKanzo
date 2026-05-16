from pypdf import PdfReader, PdfWriter


def merge_pdfs(pdf_files, output_path):

    writer = PdfWriter()

    for pdf in pdf_files:

        reader = PdfReader(pdf)

        for page in reader.pages:

            writer.add_page(page)

    with open(output_path, "wb") as file:

        writer.write(file)

import fitz


def extract_pdf_text(
    pdf_path,
    max_pages=3
):

    try:

        doc = fitz.open(pdf_path)

        text = ""

        pages = min(
            max_pages,
            len(doc)
        )

        for page_num in range(pages):

            page = doc[page_num]

            text += page.get_text()

        return text.strip()

    except Exception as e:

        print(
            f"Extraction failed: {e}"
        )

        return ""
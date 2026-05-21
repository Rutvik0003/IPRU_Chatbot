import os
import json
import shutil

from datetime import datetime

from classifier.extract_text import (
    extract_pdf_text
)

from classifier.classify import (
    classify_document
)


def save_metadata(
    metadata_path,
    metadata
):

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=4,
            ensure_ascii=False
        )


def process_pdf(pdf_path):

    print(f"\nProcessing: {pdf_path}")

    text = extract_pdf_text(pdf_path)

    if not text.strip():

        print("No text extracted")

        return

    result = classify_document(text)

    print(result)

    filename = os.path.basename(
        pdf_path
    )

    filename_without_ext = os.path.splitext(
        filename
    )[0]

    # Extract company name
    #
    # data/raw/company/file.pdf
    #
    # -> company

    company_name = os.path.basename(
        os.path.dirname(pdf_path)
    )

    metadata = {

        "company": result.company,

        "detected_company_folder": company_name,

        "insurance_type": (
            result.insurance_type
        ),

        "document_type": (
            result.document_type
        ),

        "product_name": (
            result.product_name
        ),

        "confidence": (
            result.confidence
        ),

        "is_insurance_document": (
            result.is_insurance_document
        ),

        "source_file": pdf_path,

        "processed_at": (
            datetime.utcnow().isoformat()
        )
    }

    # INSURANCE DOCUMENT
    if result.is_insurance_document:

        insurance_type = (
            result.insurance_type
            .lower()
            .strip()
        )

        destination_folder = os.path.join(
            "data",
            "processed",
            company_name,
            insurance_type
        )

        os.makedirs(
            destination_folder,
            exist_ok=True
        )

        pdf_destination = os.path.join(
            destination_folder,
            filename
        )

        metadata_destination = os.path.join(
            destination_folder,
            f"{filename_without_ext}.metadata.json"
        )

        # Move PDF
        shutil.move(
            pdf_path,
            pdf_destination
        )

        # Save metadata
        save_metadata(
            metadata_destination,
            metadata
        )

        print(
            f"Processed -> "
            f"{pdf_destination}"
        )

    # REJECTED DOCUMENT
    else:

        destination_folder = os.path.join(
            "data",
            "rejected",
            company_name
        )

        os.makedirs(
            destination_folder,
            exist_ok=True
        )

        pdf_destination = os.path.join(
            destination_folder,
            filename
        )

        metadata_destination = os.path.join(
            destination_folder,
            f"{filename_without_ext}.metadata.json"
        )

        # Move PDF
        shutil.move(
            pdf_path,
            pdf_destination
        )

        # Save metadata
        save_metadata(
            metadata_destination,
            metadata
        )

        print(
            f"Rejected -> "
            f"{pdf_destination}"
        )
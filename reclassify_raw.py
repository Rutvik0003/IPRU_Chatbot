"""
Re-run the classifier on everything still sitting in data/raw/.
Run this when raw PDFs weren't classified during the crawl
(e.g. Ollama was down at crawl time).

    python reclassify_raw.py
"""

import os
import sys
from pathlib import Path

from classifier.pipeline import process_pdf

RAW_DIR = Path("data/raw")


def main():
    pdfs = sorted(RAW_DIR.rglob("*.pdf"))
    total = len(pdfs)

    if total == 0:
        print("No PDFs in data/raw/ — nothing to do.")
        return

    print(f"Found {total} PDFs to classify\n")

    ok = failed = 0
    for i, pdf_path in enumerate(pdfs, 1):
        print(f"[{i}/{total}] {pdf_path.parent.name}/{pdf_path.name}")
        try:
            process_pdf(str(pdf_path))
            ok += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Done: {ok} classified, {failed} failed")
    print(f"  data/processed/ — insurance docs")
    print(f"  data/rejected/  — non-insurance docs")


if __name__ == "__main__":
    main()

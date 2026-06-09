"""
Rule-based processor for ICICI Prudential brochures.

Replaces the LLM classifier for IPru data — we already know every file
is a verified active-product brochure, so no LLM call is needed.

For each PDF in data/raw/ICICI_Prudential/:
  - Infer insurance_type from the subdirectory name + filename keywords
  - Clean up a human-readable product_name from the filename
  - Copy the PDF to data/processed/<COMPANY>/<insurance_type>/
  - Write a .metadata.json sidecar

Run:
    python process_ipru_raw.py
    python process_ipru_raw.py --dry-run   # print plan without moving anything
"""

import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

# -----------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------

RAW_DIR = Path("data/raw/ICICI_Prudential")
COMPANY_NAME = "ICICI Prudential Life Insurance"
COMPANY_FOLDER = "ICICI Prudential Life Insurance"
PROCESSED_BASE = Path("data/processed") / COMPANY_FOLDER
DETECTED_FOLDER = "ICICI_Prudential"

# Map raw subdirectory name (lowercased, no spaces) → insurance_type
_SUBDIR_TYPE: dict[str, str] = {
    "term_plans": "term",
    "wealth_plans": "investment",
    "retirement_plans": "investment",
    "health_plans": "health",
    "riders_plans": "unknown",
    "group_plans": "life",
    "rural_plans": "life",
}

# Ordered keyword rules applied when there is no subdirectory hint.
# First match wins, so put more-specific patterns earlier.
_KEYWORD_RULES: list[tuple[list[str], str]] = [
    # Term
    (["iprotect", "iprotectsmart", "iprotectsupreme", "iprotectsuper",
      "iprotectcare", "saraljeevanbima", "pureprot", "lifecover"], "term"),
    # Health
    (["wish", "cancer", "diabetes", "hospital", "health", "mediassure"], "health"),
    # Life (group / social)
    (["group", "pmjjby", "sarvjana", "shubhraksha", "superprotect",
      "groupterm", "loanprotect", "shubhretirement"], "life"),
    # Riders → unknown (add-ons, not standalone products)
    (["rider", "waiverof", "accidental", "disability", "criticalillness",
      "wop", "add", "goalprotect", "healthprotect"], "unknown"),
    # Investment / savings / ULIP / pension — catch-all last
    (["pension", "annuity", "retirement", "saralpension"], "investment"),
    (["gift", "signature", "platinum", "wealth", "ulip", "invest",
      "gold", "smartkid", "360", "ezygrow", "future", "savings",
      "sukh", "assured", "guaranteed", "sip", "smart", "protect"], "investment"),
]


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _infer_type(subdir: str, filename: str) -> str:
    """Determine insurance_type from the source subdirectory and filename."""
    sub_key = re.sub(r"[^a-z0-9]", "_", subdir.lower())
    if sub_key in _SUBDIR_TYPE:
        return _SUBDIR_TYPE[sub_key]

    # No subdir hint — use filename keywords
    norm = re.sub(r"[^a-z0-9]", "", filename.lower())
    for keywords, itype in _KEYWORD_RULES:
        if any(kw in norm for kw in keywords):
            return itype

    return "unknown"


def _clean_product_name(filename: str) -> str:
    """
    Turn a raw filename into a readable product name.

    ICICI_Pru_iProtect_Smart_Plus_Brochure.pdf  →  iProtect Smart Plus
    IPru-POS-iProtect-Smart-Brochure-MU-V04_Final.pdf  →  POS iProtect Smart
    ICICI Future Perfect - Brochure.pdf  →  Future Perfect
    """
    stem = Path(filename).stem
    stem = unquote(stem)

    # Replace separators with spaces
    stem = re.sub(r"[_\-]+", " ", stem)

    # Remove leading company/brand tokens (case-insensitive)
    prefixes = [
        r"^ICICI\s+Prudential\s+",
        r"^ICICI\s+Pru\s+",
        r"^ICICI\s+IPru\s+",
        r"^ICICI\s+",
        r"^ICICIPru\s+",
        r"^IPru\s+",
    ]
    for pat in prefixes:
        stem = re.sub(pat, "", stem, flags=re.IGNORECASE)

    # Remove noise words wherever they appear (not just at the end)
    noise_words = [
        r"\bBrochure\b", r"\bProspectus\b", r"\bWebview\b",
        r"\bMU\b", r"\bFinal\b", r"\bOffline\b", r"\bOnline\b",
        r"\bV\d+\b",
    ]
    for pattern in noise_words:
        stem = re.sub(pattern, "", stem, flags=re.IGNORECASE)

    # Collapse multiple spaces left behind
    stem = re.sub(r"\s{2,}", " ", stem)

    return stem.strip()


def _document_type(filename: str) -> str:
    lower = filename.lower()
    if "prospectus" in lower:
        return "brochure"   # prospectus ≈ product brochure for our purposes
    return "brochure"


# -----------------------------------------------------------------------
# Core processor
# -----------------------------------------------------------------------

def process_pdf(pdf_path: Path, dry_run: bool = False) -> dict | None:
    """
    Process one PDF. Returns the metadata dict, or None if already done.
    """
    subdir = pdf_path.parent.name if pdf_path.parent != RAW_DIR else ""
    insurance_type = _infer_type(subdir, pdf_path.name)
    product_name = _clean_product_name(pdf_path.name)
    doc_type = _document_type(pdf_path.name)

    dest_dir = PROCESSED_BASE / insurance_type
    dest_pdf = dest_dir / pdf_path.name
    dest_meta = dest_dir / (pdf_path.stem + ".metadata.json")

    # Idempotent — skip if already processed
    if dest_pdf.exists():
        return None

    metadata = {
        "company": COMPANY_NAME,
        "detected_company_folder": DETECTED_FOLDER,
        "insurance_type": insurance_type,
        "document_type": doc_type,
        "product_name": product_name,
        "confidence": 1.0,
        "is_insurance_document": True,
        "source_file": str(pdf_path).replace("\\", "/"),
        "processed_at": datetime.now().isoformat(),
    }

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, dest_pdf)
        with open(dest_meta, "w") as f:
            json.dump(metadata, f, indent=4)

    return metadata


# -----------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without copying files")
    args = parser.parse_args()

    pdfs = sorted(RAW_DIR.rglob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found under {RAW_DIR}.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Processing {len(pdfs)} PDFs\n")

    counts: dict[str, int] = {}
    skipped = 0
    done = 0

    for pdf in pdfs:
        meta = process_pdf(pdf, dry_run=args.dry_run)
        if meta is None:
            skipped += 1
            continue

        itype = meta["insurance_type"]
        counts[itype] = counts.get(itype, 0) + 1
        done += 1

        dest = PROCESSED_BASE / itype / pdf.name
        tag = "[DRY RUN]" if args.dry_run else "[DONE]"
        print(f"  {tag}  {pdf.parent.name}/{pdf.name}")
        print(f"          type={itype:<12}  product='{meta['product_name']}'")
        print(f"          → {dest}")

    print(f"\n{'='*60}")
    print(f"Processed : {done}   |   Already done (skipped): {skipped}")
    print(f"\nBreakdown by insurance_type:")
    for k, v in sorted(counts.items()):
        print(f"  {k:<15} {v} files")
    print(f"\nOutput → {PROCESSED_BASE}/")


if __name__ == "__main__":
    main()

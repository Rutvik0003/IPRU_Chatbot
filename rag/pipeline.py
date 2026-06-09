"""
RAG Ingestion Pipeline
======================
Reads every PDF from data/processed/<company>/<insurance_type>/
and for each one:
  1. Extracts full text (all pages, not just 3)
  2. Loads the .metadata.json sidecar
  3. Calls Ollama to extract 50-field taxonomy features
  4. Saves features to data/features/<company>/<stem>.features.json
  5. Chunks the text into overlapping windows
  6. Embeds chunks via sentence-transformers
  7. Upserts chunks into ChromaDB

Run:
    python -m rag.pipeline
    python -m rag.pipeline --reindex    # force re-index everything
    python -m rag.pipeline --dry-run    # print what would be indexed, don't write
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF
from dotenv import load_dotenv

load_dotenv()

from rag import chunker, embedder, vector_store
from rag.feature_extractor import extract_features
from storage import product_store

PROCESSED_DIR = Path("data/processed")


def extract_full_text(pdf_path: Path) -> str:
    try:
        doc = fitz.open(str(pdf_path))
        pages = []
        for page in doc:
            pages.append(page.get_text())
        return "\n".join(pages).strip()
    except Exception as e:
        print(f"[pipeline] Text extraction failed for {pdf_path}: {e}")
        return ""


def load_sidecar(pdf_path: Path) -> dict:
    stem = pdf_path.stem
    sidecar = pdf_path.parent / f"{stem}.metadata.json"
    if sidecar.exists():
        with open(sidecar, encoding="utf-8") as f:
            return json.load(f)
    # Infer from folder structure
    company = pdf_path.parent.parent.name
    insurance_type = pdf_path.parent.name
    return {
        "company": company,
        "insurance_type": insurance_type,
        "document_type": "brochure",
        "product_name": stem.replace("_", " ").title(),
        "source_file": str(pdf_path),
        "processed_at": datetime.utcnow().isoformat(),
        "is_insurance_document": True,
    }


def index_pdf(pdf_path: Path, force: bool = False, dry_run: bool = False):
    stem = pdf_path.stem
    company = pdf_path.parent.parent.name

    source_key = str(pdf_path)

    # Skip if already fully indexed
    already_in_store  = product_store.exists(company, stem)
    already_in_vector = vector_store.is_indexed(source_key)

    if already_in_store and already_in_vector and not force:
        print(f"[pipeline] SKIP (already indexed): {pdf_path.name}")
        return

    print(f"\n[pipeline] Indexing: {pdf_path}")

    metadata = load_sidecar(pdf_path)
    full_text = extract_full_text(pdf_path)

    if not full_text.strip():
        print(f"[pipeline] No text extracted — skipping {pdf_path.name}")
        return

    if dry_run:
        print(f"  [dry-run] Would extract + embed {len(full_text)} chars")
        return

    # ── Feature extraction ──────────────────────────────────────────────────
    if not already_in_store or force:
        features = asyncio.run(extract_features(full_text, metadata))
        product_store.save(company, stem, features)
        print(f"  [pipeline] Features saved → data/features/{company}/{stem}.features.json")
    else:
        print(f"  [pipeline] Features already exist, skipping extraction")

    # ── Vector indexing ─────────────────────────────────────────────────────
    if not already_in_vector or force:
        if force and already_in_vector:
            vector_store.delete_source(source_key)

        chunks = chunker.chunk_text(full_text)
        if not chunks:
            print(f"  [pipeline] No chunks produced — skipping vector index")
            return

        texts   = [c["text"] for c in chunks]
        embeddings = embedder.embed(texts)

        base_meta = {
            "company":          metadata.get("company", company),
            "insurance_type":   metadata.get("insurance_type", ""),
            "document_type":    metadata.get("document_type", "brochure"),
            "product_name":     metadata.get("product_name", stem),
            "source_file":      source_key,
        }

        vector_store.add_chunks(chunks, embeddings, base_meta)
        print(f"  [pipeline] {len(chunks)} chunks indexed in ChromaDB")
    else:
        print(f"  [pipeline] Vector already indexed, skipping")


def run(force: bool = False, dry_run: bool = False, company: str = None):
    if not PROCESSED_DIR.exists():
        print(f"[pipeline] {PROCESSED_DIR} does not exist. Run the crawler first.")
        return

    pdf_paths = sorted(PROCESSED_DIR.rglob("*.pdf"))

    if company:
        pdf_paths = [p for p in pdf_paths if company.lower() in p.parts[-3].lower()]
        print(f"[pipeline] Company filter: '{company}'")

    if not pdf_paths:
        print(f"[pipeline] No PDFs found in {PROCESSED_DIR}")
        return

    print(f"[pipeline] Found {len(pdf_paths)} PDFs to process")

    for pdf_path in pdf_paths:
        try:
            index_pdf(pdf_path, force=force, dry_run=dry_run)
        except Exception as e:
            print(f"[pipeline] ERROR on {pdf_path}: {e}")
            continue

    if not dry_run:
        total = vector_store.count()
        print(f"\n[pipeline] Done. ChromaDB total chunks: {total}")
        print(f"[pipeline] Feature files: {len(product_store.list_all_paths())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex",  action="store_true", help="Force re-index all PDFs")
    parser.add_argument("--dry-run",  action="store_true", help="Scan only, don't write")
    parser.add_argument("--company",  type=str, default=None, help="Filter by company name substring")
    args = parser.parse_args()

    run(force=args.reindex, dry_run=args.dry_run, company=args.company)

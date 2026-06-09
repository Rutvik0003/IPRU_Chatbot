"""
Targeted ICICI Prudential brochure fetcher.

Strategy:
  1. Fetch active-and-withdrawn-products-list.html → whitelist of active product names
  2. Fetch download-centre.html → all brochure PDF links
  3. Cross-reference: only keep PDFs whose filename matches an active product name
  4. Download matched PDFs to data/raw/ICICI_Prudential/
  5. Queue each file for the classifier worker
"""

import asyncio
import os
import re
from urllib.parse import unquote, urljoin

import aiofiles
from bs4 import BeautifulSoup
from curl_cffi import requests

from crawler.logger import logger
from crawler.utils import sanitize_filename
from shared.queue_manager import pdf_queue

IPRU_BASE = "https://www.iciciprulife.com"
ACTIVE_PRODUCTS_URL = f"{IPRU_BASE}/icici-pru-active-and-withdrawn-products-list.html"
DOWNLOAD_CENTER_URL = f"{IPRU_BASE}/services/download-centre.html"
COMPANY_NAME = "ICICI_Prudential"
RAW_DIR = f"data/raw/{COMPANY_NAME}"

_IMPERSONATE = "chrome120"
_BATCH_SIZE = 5
_BATCH_DELAY = 2


def _normalize(text: str) -> str:
    """Lowercase, strip 'icici pru' prefix and all non-alphanumeric chars."""
    text = text.lower()
    text = re.sub(r"icici\s*pru\s*", "", text)
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def _all_existing_filenames() -> set[str]:
    """Return lowercased filenames of every PDF already in RAW_DIR (recursive)."""
    found: set[str] = set()
    if not os.path.exists(RAW_DIR):
        return found
    for root, _, files in os.walk(RAW_DIR):
        for f in files:
            if f.lower().endswith(".pdf"):
                found.add(f.lower())
    return found


# ---------------------------------------------------------------------------
# Phase 1 — active products
# ---------------------------------------------------------------------------

async def _fetch_active_products(session) -> set[str]:
    print("[1/3] Fetching active products list...")
    r = await session.get(ACTIVE_PRODUCTS_URL, timeout=30)
    if r.status_code != 200:
        logger.error(f"Active products page HTTP {r.status_code}")
        return set()

    html = r.text
    soup = BeautifulSoup(html, "lxml")

    # Locate the "List of withdrawn products" divider in raw HTML
    withdrawn_pos = html.lower().find("list of withdrawn")
    if withdrawn_pos < 0:
        logger.warning("Could not find 'withdrawn' divider; treating all tables as active")
        withdrawn_pos = len(html)

    # Find start position of every <table> tag
    table_tag_positions = [m.start() for m in re.finditer(r"<table", html, re.IGNORECASE)]
    all_tables = soup.find_all("table")

    active_names: set[str] = set()
    for i, (table, tag_pos) in enumerate(zip(all_tables, table_tag_positions)):
        if tag_pos >= withdrawn_pos:
            break  # all remaining tables are withdrawn
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if cols:
                name = cols[0].get_text(strip=True)
                if name and len(name) > 3:
                    active_names.add(name)

    print(f"       Active products/riders found: {len(active_names)}")
    return active_names


# ---------------------------------------------------------------------------
# Phase 2 — brochure URLs from download centre
# ---------------------------------------------------------------------------

async def _fetch_brochure_urls(session) -> list[tuple[str, str]]:
    """Return list of (filename, full_url) for brochure PDFs only."""
    print("[2/3] Fetching download centre...")
    r = await session.get(DOWNLOAD_CENTER_URL, timeout=30)
    if r.status_code != 200:
        logger.error(f"Download centre HTTP {r.status_code}")
        return []

    soup = BeautifulSoup(r.text, "lxml")
    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    # Keywords that mark non-brochure links we want to skip
    _skip_in_url = ("claim", "application", "proposal", "form",
                    "kyc", "mandate", "neft", "cheque")
    # We want brochures and prospectus; skip policy wording for now
    _keep_in_url = ("brochure", "prospectus")

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        href_lower = href.lower()

        if ".pdf" not in href_lower:
            continue
        if any(kw in href_lower for kw in _skip_in_url):
            continue
        if not any(kw in href_lower for kw in _keep_in_url):
            continue

        full_url = urljoin(IPRU_BASE, href)
        if full_url in seen:
            continue
        seen.add(full_url)

        filename = unquote(full_url.split("/")[-1])
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        results.append((filename, full_url))

    print(f"       Unique brochure/prospectus PDFs found: {len(results)}")
    return results


# ---------------------------------------------------------------------------
# Phase 3 — match & cross-verify
# ---------------------------------------------------------------------------

def _match_brochures_to_active(
    brochures: list[tuple[str, str]],
    active_names: set[str],
) -> tuple[list[tuple[str, str, str]], set[str]]:
    """
    Returns:
      matched  — list of (filename, url, matched_product_name)
      unmatched_active — active products with no brochure found
    """
    unmatched = set(active_names)
    matched: list[tuple[str, str, str]] = []

    for filename, url in brochures:
        norm_file = _normalize(filename)
        for product in active_names:
            norm_prod = _normalize(product)
            if len(norm_prod) < 6:
                continue
            if norm_prod in norm_file:
                matched.append((filename, url, product))
                unmatched.discard(product)
                break  # first match wins

    return matched, unmatched


def _cross_verify_existing(
    existing_files: set[str],
    active_names: set[str],
) -> None:
    print("\n--- Cross-verifying existing files in data/raw/ICICI_Prudential/ ---")
    active_matches: list[tuple[str, str]] = []
    unknown: list[str] = []

    for fname in sorted(existing_files):
        norm_file = _normalize(fname)
        hit = None
        for product in active_names:
            norm_prod = _normalize(product)
            if len(norm_prod) < 6:
                continue
            if norm_prod in norm_file:
                hit = product
                break
        if hit:
            active_matches.append((fname, hit))
        else:
            unknown.append(fname)

    print(f"  [ACTIVE]   {len(active_matches)} existing files match an active product")
    for f, p in active_matches:
        print(f"             {f}  →  {p}")

    print(f"  [UNKNOWN]  {len(unknown)} existing files have NO active product match")
    print("             (may be withdrawn, riders, or group plans not covered by brochures)")
    for f in unknown:
        print(f"             {f}")


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

async def _download_one(session, url: str, filename: str) -> str | None:
    os.makedirs(RAW_DIR, exist_ok=True)
    filepath = os.path.join(RAW_DIR, sanitize_filename(filename))

    if os.path.exists(filepath):
        return filepath  # already downloaded

    try:
        r = await session.get(url, timeout=60)
        if r.status_code != 200:
            logger.warning(f"Download skipped {url}: HTTP {r.status_code}")
            return None

        content_type = r.headers.get("Content-Type", "").lower()
        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
            logger.warning(f"Non-PDF content-type at {url}: {content_type}")
            return None

        async with aiofiles.open(filepath, "wb") as f:
            await f.write(r.content)

        print(f"  [DOWNLOADED] {filename}")
        logger.info(f"Downloaded: {url} → {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Download error {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

async def run_ipru_targeted():
    print("\n========= ICICI Prudential Targeted Brochure Fetcher =========\n")

    existing_files = _all_existing_filenames()
    print(f"Existing PDFs in {RAW_DIR}: {len(existing_files)}\n")

    async with requests.AsyncSession(impersonate=_IMPERSONATE) as session:

        active_names = await _fetch_active_products(session)
        if not active_names:
            print("ABORT: failed to load active products.")
            return

        brochures = await _fetch_brochure_urls(session)
        if not brochures:
            print("ABORT: failed to load download centre.")
            return

        matched, unmatched_active = _match_brochures_to_active(brochures, active_names)
        print(f"\n[3/3] Matched {len(matched)} brochures to active products")
        print(f"      Active products with no brochure on download centre: {len(unmatched_active)}")
        if unmatched_active:
            for name in sorted(unmatched_active):
                print(f"        (no brochure) {name}")

        _cross_verify_existing(existing_files, active_names)

        # Filter to only files not yet downloaded
        to_download = [
            (fn, url, prod)
            for fn, url, prod in matched
            if sanitize_filename(fn).lower() not in existing_files
        ]
        print(f"\nNew brochures to download: {len(to_download)}")

        if not to_download:
            print("All matched brochures are already downloaded. Nothing to do.")
            return

        print(f"\nDownloading in batches of {_BATCH_SIZE}...\n")
        downloaded, failed = 0, 0

        for i in range(0, len(to_download), _BATCH_SIZE):
            batch = to_download[i : i + _BATCH_SIZE]
            tasks = [_download_one(session, url, fn) for fn, url, _ in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result, (fn, url, prod) in zip(results, batch):
                if isinstance(result, Exception):
                    logger.error(f"Batch error {url}: {result}")
                    failed += 1
                elif result:
                    await pdf_queue.put(result)
                    downloaded += 1
                else:
                    failed += 1

            await asyncio.sleep(_BATCH_DELAY)

        print(f"\n========= Done =========")
        print(f"  Downloaded : {downloaded}")
        print(f"  Failed     : {failed}")
        print(f"  Queued for classification: {downloaded}\n")


if __name__ == "__main__":
    asyncio.run(run_ipru_targeted())

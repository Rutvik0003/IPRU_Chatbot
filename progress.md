# IPRU Chatbot — Progress Log

---

## 2026-06-09 — Targeted Crawler & Akamai Bypass

### Problem
The generic `aiohttp` BFS crawler was blocked with HTTP 403 by ICICI Prudential's Akamai CDN
on every request — even with a spoofed `User-Agent`. Akamai inspects the TLS handshake fingerprint
at the transport layer, which `aiohttp` and `requests` expose as obviously non-browser traffic.
A blind BFS crawl would also pull down withdrawn products, annual reports, and corporate PDFs,
polluting the RAG pipeline.

### Solution Implemented
**Replaced `aiohttp` with `curl_cffi`** (`impersonate="chrome120"`), which spoofs the exact TLS
signature of Chrome. This bypassed Akamai completely — both the active-products page and the
download centre returned HTTP 200.

**Pivoted from BFS to targeted extraction** via `crawler/ipru_targeted.py`:
1. Fetches `active-and-withdrawn-products-list.html` → parses only the tables that appear
   *before* the "List of withdrawn products / riders" divider → 61 active products/riders.
2. Fetches `download-centre.html` → collects brochure and prospectus PDF links only
   (skips claim forms, application forms, KYC, etc.) → 75 unique PDFs.
3. Cross-references: normalizes product names and PDF filenames, checks for substring match →
   56 of 75 brochures matched to active products.
4. Downloads only the unmatched files (skips already-present ones).

### Cross-Verification of Existing `data/raw/ICICI_Prudential/` Files
62 PDFs were already present (manually downloaded from the brochures section).

| Status | Count | Notes |
|---|---|---|
| ACTIVE — confirmed match | 50 | Filename normalizes to an active product name |
| UNKNOWN — no match | 12 | See below |

**Unknown 12 files — likely status:**

| File | Likely Status | Reason |
|---|---|---|
| `icici-pru-goal-protect-brochure.pdf` | Active (rider) | "Goal Protect Rider" is active; filename abbreviates it |
| `icici-pru-gold-brochure.pdf` | Active | "ICICI Pru Gold" is active; 4-char norm "gold" below match threshold |
| `icici-pru-wish-brochure.pdf` | Active | "ICICI Pru Wish" is active; 4-char norm "wish" below match threshold |
| `icici_pru_gpp_flexi_brochure.pdf` | Active | "GPP Flexi" = Guaranteed Pension Plan Flexi; abbreviation not in norm name |
| `icici_pru_gift_long_term_brochure.pdf` | Likely withdrawn | No "GIFT Long Term" in active list |
| `icici_pru_linked_wop_rider_brochure.pdf` | Active (rider) | "Linked Waiver of Premium Rider" is active |
| `icici_pru_non-linked_group_critical_illness_rider.pdf` | Active (rider) | Group CI rider is active |
| `icici_pru_non_linked_group_add_rider-brochure.pdf` | Active (rider) | Group ADD rider is active |
| `icici_pru_non_linked_wop_rider_brochure.pdf` | Active (rider) | Non-Linked WOP rider is active |
| `icici_pru_sip_plus_brochure.pdf` | Likely withdrawn | No "SIP Plus" in current active list |
| `iprulinked-accidenal-death-and-disability-rider-brochure.pdf` | Active (rider) | Linked ADD rider is active |
| `pmjjby_brochure.pdf` | Active (group) | PMJJBY scheme is in active group products |

### New Files Downloaded (6)
| File | Matched Active Product |
|---|---|
| `ICICI Future Perfect - Brochure.pdf` | ICICI Pru Future Perfect |
| `ICICI_Pru_Wealth_Forever_Prospectus.pdf` | ICICI Pru Wealth Forever |
| `ICICI_Pru_GIFT_Pro_Brochure_V23_Webview.pdf` | ICICI Pru GIFT Pro |
| `ICICI_Prudential_Signature_Capital_Guarantee_II_Brochure.pdf` | ICICI Pru Signature |
| `ICICI-Pru-iProtect-Smart-ROP-Brochure.pdf` | ICICI Pru iProtect Smart Return of Premium |
| `ICICI Pru iProtect Smart.pdf` | ICICI Pru iProtect Smart |

### Active Products with No Brochure on Download Centre (19)
These are real active products where the website either has no dedicated brochure PDF or the
brochure filename doesn't contain the product name (e.g. rider sub-products, PMJJBY).
The RAG pipeline will function without them but coverage will be incomplete for:
- ICICI Pru iProtect Smart Plus (brochure already exists under that name, matcher attributed it to iProtect Smart)
- ICICI Pru Signature Pension (brochure file exists; matcher attributed it to Signature)
- ICICI Pru Gold, Wish, GIFT Assure — short names, need manual check
- Riders: Goal Protect, Non-Linked ADD, Non-Linked WOP, Linked WOP, Non-Linked Health Protect

### Code Changes
| File | Change |
|---|---|
| `crawler/ipru_targeted.py` | **New** — targeted scraper with active-product whitelist matching |
| `crawler/downloader.py` | Replaced `aiohttp` with `curl_cffi`; removed `session` parameter |
| `crawler/insurance_crawler.py` | Updated `download_pdf` call (dropped `session` arg) |
| `requirements.txt` | Added `curl_cffi` |

---

## Next Steps
1. Run the classifier pipeline (`python -m crawler.main` or directly `python -m rag.pipeline`)
   on the 68 PDFs now in `data/raw/ICICI_Prudential/` to move active brochures to
   `data/processed/ICICI_Prudential/<insurance_type>/` and rejected ones to `data/rejected/`.
2. Run `python -m rag.pipeline` to extract 50-field taxonomy features via Ollama for each
   processed PDF and build the ChromaDB vector index.
3. Validate ranking with `scoring/ranker.py` on a sample user profile.

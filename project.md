# IPRU Chatbot — Pre-RAG Pipeline

This document describes what the existing codebase does. Everything here feeds into your RAG pipeline — it doesn't exist yet.

---

## What This System Does (End-to-End)

```
insurer website
      │
      ▼
[Crawler] ──── rejects non-insurance PDFs by filename ────► (dropped)
      │
      ▼ downloads to data/raw/<company>/
[Queue] (asyncio.Queue, shared between crawler and classifier)
      │
      ▼
[Classifier Worker] — throttled async consumer
      │
      ├── extract_text.py   → PyMuPDF reads first 3 pages
      ├── classify.py       → LLM call via OpenRouter → JSON
      └── pipeline.py       → move PDF + write .metadata.json
            │
            ├── is_insurance_document = True  → data/processed/<company>/<insurance_type>/
            └── is_insurance_document = False → data/rejected/<company>/
```

**Your RAG pipeline starts at `data/processed/`.**

---

## Module Breakdown

### `crawler/` — Async Web Crawler

**Entry:** `crawler/main.py` → `asyncio.run(run())`

- Reads `config/insurers.yaml` for company list
- Starts N classifier workers (currently hardcoded to 1)
- Launches one `InsuranceCrawler` per company concurrently
- Waits for all crawlers to finish, then drains the queue

**`InsuranceCrawler` (insurance_crawler.py)**

- BFS traversal using a `deque`, starting from the company homepage
- Stays within the same domain (`is_same_domain()`)
- Skips `mailto:`, `javascript:`, `tel:` links
- Detects PDFs two ways: URL contains `.pdf`, or `Content-Type: application/pdf`
- Before downloading, runs the filename through two filters:
  - `should_reject_file()` — drops it if it matches any REJECT keyword
  - `is_priority_insurance_file()` — flags it (logged, still downloaded)
- Tracks: pages crawled, PDFs found, rejected count, priority count, error count
- Prints a per-company summary on completion

**Constants (`crawler/config.py`)**

| Setting | Value |
|---|---|
| MAX_DEPTH | 5 |
| MAX_CONCURRENT_REQUESTS | 20 |
| REQUEST_TIMEOUT | 30s |
| PDF_TIMEOUT | 60s |
| User-Agent | Chrome 136 on Windows |

**`downloader.py`**

- Downloads PDF via aiohttp, validates `Content-Type` contains `"pdf"`
- Sanitizes filename (strips non-alphanumeric chars)
- Skips if file already exists at destination (deduplication)
- Saves to `data/raw/<company_name>/<filename>.pdf`
- After saving, puts the filepath onto `pdf_queue`
- Retry: 3 attempts, 2s fixed wait (Tenacity)

**`logger.py`**

- Writes to `data/logs/crawler.log`
- Captures: fetch failures, download failures, rejected filenames, downloaded URLs, per-company summary

---

### `shared/` — Cross-Module Utilities

**`queue_manager.py`**

- Single `asyncio.Queue()` instance (`pdf_queue`) shared by the downloader and the classifier worker
- The crawler puts filepaths in; the classifier worker consumes them

**`file_filter.py`**

Two keyword lists matched against normalized filenames (lowercased, non-alphanumeric → space):

- **PRIORITY_KEYWORDS** (~80 terms) — insurance-signal words: `policy`, `brochure`, `premium`, `health`, `term`, `ulip`, `motor`, `travel`, `claim`, `rider`, `renewal`, etc.
- **REJECT_KEYWORDS** (~70 terms) — corporate noise to drop: `annual`, `investor`, `governance`, `esg`, `tender`, `gst`, `career`, `press-release`, `loan`, `mutual-fund`, etc.

Functions:
- `should_reject_file(filename) -> bool` — returns True if any reject keyword matches
- `is_priority_insurance_file(filename) -> bool` — returns True if any priority keyword matches

---

### `classifier/` — LLM-Based Document Classifier

**`extract_text.py`**

- Uses PyMuPDF (`fitz`) to open a PDF and extract text from the **first 3 pages**
- Returns empty string on failure (handled gracefully downstream)

**`classify.py`**

- LLM: OpenRouter API (`openai/gpt-oss-120b:free` currently; Gemini and DeepSeek commented out as alternatives)
- Sends first 10,000 chars of extracted text to the LLM
- System prompt instructs it to return strict JSON only
- Retry: up to 2 attempts; exponential backoff on 429 rate-limit errors
- Parses response with regex to handle markdown-wrapped JSON
- Sanitizes all fields with safe defaults if model omits any

**LLM Output Schema**

| Field | Type | Possible Values |
|---|---|---|
| `is_insurance_document` | bool | true / false |
| `document_type` | str | brochure, policy_wording, claim_form, annual_report, disclosure, tax_document, advertisement, other |
| `insurance_type` | str | health, term, life, motor, travel, investment, unknown |
| `company` | str | free text extracted from document |
| `product_name` | str | free text extracted from document |
| `confidence` | float | 0.0 – 1.0 |

**`schemas.py`**

Pydantic model `InsuranceDocument` — validates and holds the LLM output with safe defaults for all fields.

**`pipeline.py` — Core Processing Logic**

`process_pdf(pdf_path)`:
1. Extracts text (first 3 pages via PyMuPDF)
2. Classifies via LLM → `InsuranceDocument`
3. Builds a metadata dict
4. Routes the PDF:
   - **Insurance document** → moved to `data/processed/<company>/<insurance_type>/`
   - **Not insurance** → moved to `data/rejected/<company>/`
5. Saves a `.metadata.json` file alongside each PDF

**`worker.py`**

- Async consumer of `pdf_queue`
- Runs `process_pdf()` in a thread (`asyncio.to_thread`) so blocking I/O doesn't stall the event loop
- 5-second sleep between jobs (rate-limit throttle for OpenRouter)
- Calls `pdf_queue.task_done()` in `finally` so `queue.join()` works correctly

---

## Data Directory Structure (Runtime)

```
data/
├── raw/
│   └── <Company Name>/          ← staging area; PDFs land here first
│       └── some_brochure.pdf
│
├── processed/
│   └── <Company Name>/
│       └── <insurance_type>/    ← e.g. health/, term/, motor/
│           ├── brochure.pdf
│           └── brochure.metadata.json
│
├── rejected/
│   └── <Company Name>/
│       ├── annual_report.pdf
│       └── annual_report.metadata.json
│
└── logs/
    └── crawler.log
```

---

## Metadata File Format

Every processed or rejected PDF gets a `.metadata.json` sidecar:

```json
{
    "company": "ICICI Prudential Life Insurance",
    "detected_company_folder": "ICICI Prudential Life Insurance",
    "insurance_type": "term",
    "document_type": "brochure",
    "product_name": "iProtect Smart",
    "confidence": 0.95,
    "is_insurance_document": true,
    "source_file": "data/raw/ICICI Prudential Life Insurance/iprotect_smart.pdf",
    "processed_at": "2026-06-08T10:00:00"
}
```

---

## Configuration

**`config/insurers.yaml`** — company list (currently one entry):

```yaml
companies:
  - name: ICICI Prudential Life Insurance
    url: https://www.iciciprulife.com/
```

Add more companies here; the crawler will run one per company concurrently.

**Environment variables** (`.env`):

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | LLM API key for classification |

---

## Dependencies

| Package | Used For |
|---|---|
| `aiohttp` | Async HTTP requests (crawling + downloading) |
| `beautifulsoup4` + `lxml` | HTML parsing, link extraction |
| `aiofiles` | Async file writes |
| `tenacity` | Retry logic on download failures |
| `tqdm` | Progress bars |
| `pyyaml` | Config file parsing |
| `pymupdf` (fitz) | PDF text extraction |
| `openai` | OpenRouter-compatible API client |
| `pydantic` | Schema validation for LLM output |
| `python-dotenv` | `.env` loading |

---

---

## RAG Pipeline (new — `rag/` + `scoring/` + `storage/`)

### Full Data Flow

```
data/processed/<company>/<insurance_type>/brochure.pdf
                                          brochure.metadata.json
         │
         ▼  python -m rag.pipeline
[rag/pipeline.py]
    ├── extract full text (all pages, PyMuPDF)
    ├── load .metadata.json sidecar
    ├── [rag/feature_extractor.py] ─── Ollama (gemma3:4b)
    │       Extract 50-field taxonomy in 8 focused section calls
    │       Validate + merge → data/features/<company>/<stem>.features.json
    ├── [rag/chunker.py] → overlapping word-count chunks (~350 words, 40 overlap)
    ├── [rag/embedder.py] → sentence-transformers all-MiniLM-L6-v2
    └── [rag/vector_store.py] → ChromaDB (data/chroma/, cosine similarity)
         │
         ▼
[rag/query_engine.py]   — hybrid BM25 + vector retrieval (RRF merge)
         │
         ▼
[scoring/profile_mapper.py]   — onboarding answers → UserProfile + weights
[scoring/scorer.py]           — score_product() → 0-100 with dimension breakdown
[scoring/ranker.py]           — rank_ipru() / rank_competitors()
[scoring/gap_analysis.py]     — compute_gap() → [-100, +100] per feature + radar data
```

---

### `rag/` Module

**`pipeline.py`** — Entry point. Run: `python -m rag.pipeline [--reindex] [--dry-run]`
- Scans `data/processed/` recursively for PDFs
- Idempotent: skips already-indexed files (check both feature store + ChromaDB)
- `--reindex` forces full re-extraction and re-embedding
- `--dry-run` scans without writing

**`feature_extractor.py`** — LLM-based structured extraction via Ollama
- Configured via `OLLAMA_URL` and `OLLAMA_MODEL` env vars (default: `gemma3:4b`)
- Splits the 50-field taxonomy into 8 focused sections — extracts one section per call
- System prompt enforces null discipline: "if not in text → null, never guess"
- Post-extraction: type-validates and range-clamps every field
- Merges per-section results (non-null wins; min for min_* fields, max for max_*)

**`chunker.py`** — `chunk_text(text, chunk_words=350, overlap_words=40) -> list[dict]`
- Tries to detect section boundaries (insurance section headers)
- Returns `{text, index, section, word_count}` per chunk

**`embedder.py`** — `embed(texts) -> list[list[float]]`
- Lazy-loads `all-MiniLM-L6-v2`, batch=32, L2-normalized

**`vector_store.py`** — ChromaDB wrapper
- `is_indexed(source_file)`, `add_chunks()`, `query()`, `delete_source()`, `count()`
- Stored metadata per chunk: company, insurance_type, document_type, product_name, chunk_index, section, source_file

**`query_engine.py`** — `QueryEngine.retrieve(query, top_k, profile, filters)`
- Vector search from ChromaDB
- BM25 over product feature summaries (graceful fallback if rank_bm25 not installed)
- Reciprocal Rank Fusion (RRF, k=60) to merge both result lists

---

### `scoring/` Module

**`taxonomy.py`** — `FEATURE_TAXONOMY` (50 fields) + `SECTIONS` grouping

**`weights.py`** — `DIMENSION_WEIGHTS`, `FEATURE_DIM_WEIGHTS`, `PROFILE_MULTIPLIERS`, `HARD_FILTER_RULES`
- 6 dimensions: protection (28%), returns (24%), flexibility (20%), eligibility (12%), riders (10%), charges (6%)
- Multipliers applied per: goal, risk, dependents, liquidity, health_risk, maturity

**`profile_mapper.py`** — `map_profile(answers: dict) -> dict`
- Accepts 8 onboarding question answers
- Returns: hard_filters, product_type_filter, feature_weights (normalised to sum=1), profile_label

**`scorer.py`** — `score_product(features, profile) -> dict`
- Applies hard filters first (returns None if fails)
- Maps feature values to {0.0, 0.5, 1.0} with field-specific logic
- Computes weighted total (0-100), per-dimension breakdown, matched/missing features

**`ranker.py`** — `rank_ipru(profile, top_k=5)` / `rank_competitors(profile, top_k=5)` / `rank_all(profile)`
- Loads all feature JSONs from `storage/`, identifies IPru vs competitor by company name
- Scores + hard-filters + sorts

**`gap_analysis.py`** — `compute_gap(ipru_features, competitor_features, profile) -> dict`
- Returns: gap_score (-100 to +100), per-feature gaps, advantages, trails, dimension_gaps, radar_data (formatted for Recharts RadarChart)

---

### `storage/` Module

**`product_store.py`** — JSON file store at `data/features/<company>/<stem>.features.json`
- `save()`, `load_all(insurer_filter)`, `load_one()`, `exists()`, `list_all_paths()`

---

### LLM Usage Contract

| Stage | LLM? | Why |
|---|---|---|
| Feature extraction | YES (Ollama) | Unstructured text → structured JSON, semantic synonyms |
| Chunking | No | Deterministic word-count split |
| Embedding | No | sentence-transformers model, no LLM |
| Retrieval | No | Vector similarity + BM25 math |
| Scoring | No | Pure weighted arithmetic |
| Ranking | No | Sort by numeric score |
| Gap analysis | No | Subtraction + weighted sum |

**Ollama vs OpenRouter for extraction:**
OpenRouter free tier → ~10-20 req/min, 100 PDFs × 8 sections = 800 calls = hours + rate limits.
Ollama local → no rate limits, ~2-4s/call, 800 calls ≈ 45 min, runs offline.

---

### Feature Data Directory

```
data/
├── features/
│   └── <Company Name>/
│       └── <stem>.features.json    ← 50-field taxonomy + _meta sidecar
├── chroma/                         ← ChromaDB persistent index
└── processed/ ...                  ← input (from classifier)
```

### Feature JSON Format

```json
{
  "_meta": {
    "company": "ICICI Prudential Life Insurance",
    "insurance_type": "term",
    "document_type": "brochure",
    "product_name": "iProtect Smart",
    "source_file": "data/processed/...",
    "extracted_at": "2026-06-08T10:00:00",
    "extraction_model": "gemma3:4b"
  },
  "product_name": "ICICI Pru iProtect Smart",
  "insurer": "ICICI Prudential Life Insurance",
  "product_type": "term",
  "min_entry_age": 18,
  "max_entry_age": 65,
  "terminal_illness_inbuilt": true,
  "critical_illness_rider": true,
  "ci_illnesses_covered": 34,
  "return_of_premium": false,
  "whole_life_option": true,
  ...
}
```

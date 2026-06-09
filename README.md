# IPRU Chatbot — Insurance Product Gap Analysis Tool

> **Team Kappa** · ICICI Prudential Life Insurance · RAG-powered product recommender

A three-stage system that scrapes insurance brochures, extracts structured features using an LLM, and ranks ICICI Pru products against a user's financial profile through a Streamlit UI.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SYSTEM ARCHITECTURE                             │
│                                                                         │
│  STAGE 1 — DATA                STAGE 2 — RAG                STAGE 3    │
│  ─────────────────             ─────────────────            ────────   │
│                                                                         │
│  Insurer Website               Feature Extraction           Streamlit  │
│       │                         (Ollama LLM)                   UI      │
│       ▼                               │                        │       │
│  Web Crawler ──► data/raw/      ┌─────▼──────┐           ┌────▼─────┐ │
│  (curl_cffi)       PDFs         │  50-field  │           │  8-Qn    │ │
│       │                         │  taxonomy  │           │ Wizard   │ │
│       ▼                         │  per PDF   │           └────┬─────┘ │
│  Classifier ──► data/processed/ └─────┬──────┘                │       │
│  (rule-based)   + .metadata.json      │                        ▼       │
│                                       ▼                   Profile      │
│                              data/features/   ──────►    Mapper        │
│                              .features.json               │            │
│                                       │                   ▼            │
│                                       ▼               Scorer /         │
│                              ChromaDB Vectors         Ranker           │
│                              data/chroma/              │               │
│                                                        ▼               │
│                                                  Top-5 Products        │
│                                                  + Match Scores        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## What Is Built (Current State)

### ✅ Stage 1 — Data Collection (ICICI Pru: Complete)

| Component | File | Status |
|-----------|------|--------|
| Generic BFS web crawler | `crawler/insurance_crawler.py` | ✅ Done |
| ICICI Pru targeted crawler (Akamai bypass) | `crawler/ipru_targeted.py` | ✅ Done |
| PDF downloader (curl_cffi TLS spoof) | `crawler/downloader.py` | ✅ Done |
| Rule-based classifier → metadata sidecars | `process_ipru_raw.py` | ✅ Done |
| 68 ICICI Pru active brochures downloaded | `data/raw/ICICI_Prudential/` | ✅ Done |
| 68 processed PDFs + `.metadata.json` sidecars | `data/processed/ICICI Prudential Life Insurance/` | ✅ Done |

### ✅ Stage 2 — RAG Pipeline (ICICI Pru: Complete)

| Component | File | Status |
|-----------|------|--------|
| Async LLM feature extraction (8 sections, parallel) | `rag/feature_extractor.py` | ✅ Done |
| Text chunker (1000-char overlapping windows) | `rag/chunker.py` | ✅ Done |
| Sentence-transformer embedder (all-MiniLM-L6-v2) | `rag/embedder.py` | ✅ Done |
| ChromaDB vector store | `rag/vector_store.py` | ✅ Done |
| Hybrid BM25 + vector query engine (RRF merge) | `rag/query_engine.py` | ✅ Done |
| End-to-end ingestion pipeline | `rag/pipeline.py` | ✅ Done |
| 68 feature JSONs (50 fields each) | `data/features/` | ✅ Done |
| 1,695 vector chunks in ChromaDB | `data/chroma/` | ✅ Done |

### ✅ Stage 3 — Scoring & UI (ICICI Pru: Complete)

| Component | File | Status |
|-----------|------|--------|
| 50-field feature taxonomy | `scoring/taxonomy.py` | ✅ Done |
| User profile mapper (8-question → weights) | `scoring/profile_mapper.py` | ✅ Done |
| Weighted feature scorer | `scoring/scorer.py` | ✅ Done |
| Product ranker with deduplication | `scoring/ranker.py` | ✅ Done |
| Gap analysis (IPru vs competitors) | `scoring/gap_analysis.py` | ✅ Done |
| Streamlit UI — 8-question wizard + results | `app.py` | ✅ Done |

### 🔲 What Still Needs to Be Done

| Task | Notes |
|------|-------|
| Expand crawling to other insurers | LIC, HDFC Life, Bajaj Allianz, SBI Life etc. |
| Re-run RAG pipeline for each new insurer | Same pipeline, just point at new processed/ folder |
| Cross-insurer comparison in UI | Show "IPru vs Competitor" gap analysis |
| Improve feature extraction accuracy | Some fields like `min_entry_age` often null — needs prompt tuning |
| Richer UI — product detail page | Show full brochure excerpt, download link, etc. |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Crawling | `curl_cffi` (Chrome TLS fingerprint spoof), `aiohttp`, Playwright |
| PDF text extraction | `PyMuPDF` (fitz) |
| LLM inference | Ollama (`gemma4:31b-cloud`) — runs locally |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim, offline) |
| Vector store | `ChromaDB` (cosine similarity, persistent) |
| Keyword search | `rank_bm25` (BM25Okapi) |
| UI | `Streamlit` + `Plotly` |
| Config | `python-dotenv`, `PyYAML` |

---

## Project Structure

```
IPRU_Chatbot/
│
├── app.py                        # Streamlit UI entry point
├── .env                          # API keys / model config (not committed)
├── .env.example                  # Template for .env
├── requirements.txt
│
├── crawler/
│   ├── insurance_crawler.py      # Generic BFS crawler (all insurers)
│   ├── ipru_targeted.py          # ICICI Pru targeted crawler (Akamai bypass)
│   ├── downloader.py             # PDF downloader (curl_cffi)
│   ├── config.py                 # Crawler settings
│   └── main.py                   # Crawler CLI entry point
│
├── classifier/
│   └── classify.py               # LLM-based PDF classifier (used for non-IPru)
│
├── process_ipru_raw.py           # Rule-based classifier for ICICI Pru data
├── reclassify_raw.py             # Re-run classification on existing raw files
│
├── rag/
│   ├── pipeline.py               # Main ingestion pipeline (run this to index)
│   ├── feature_extractor.py      # Async LLM extraction — 8 parallel Ollama calls/PDF
│   ├── chunker.py                # Overlapping text windows
│   ├── embedder.py               # sentence-transformers wrapper
│   ├── vector_store.py           # ChromaDB read/write
│   └── query_engine.py           # Hybrid BM25 + vector retrieval (RRF merge)
│
├── scoring/
│   ├── taxonomy.py               # 50-field feature schema across 8 sections
│   ├── weights.py                # Dimension weights + profile multipliers
│   ├── profile_mapper.py         # 8 user answers → feature weight vector
│   ├── scorer.py                 # Score one product against a profile
│   ├── ranker.py                 # Rank all IPru products; deduplicate
│   └── gap_analysis.py           # IPru vs competitor gap computation
│
├── storage/
│   └── product_store.py          # Read/write .features.json files
│
├── config/
│   └── insurers.yaml             # Per-insurer crawler config
│
├── data/                         # Runtime data — NOT committed (see .gitignore)
│   ├── raw/                      # Downloaded PDFs, organized by insurer
│   ├── processed/                # PDFs + .metadata.json sidecars
│   ├── features/                 # .features.json per PDF (committed — small)
│   └── chroma/                   # ChromaDB vector index (not committed)
│
└── progress.md                   # Detailed crawl + pipeline run log
```

---

## Setup

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/) installed and running locally
- The `gemma4:31b-cloud` model pulled in Ollama (or update `.env` with your model)

### 1 — Clone and install

```bash
git clone https://github.com/Rutvik0003/IPRU_Chatbot.git
cd IPRU_Chatbot
git checkout rag

pip install -r requirements.txt
```

### 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:31b-cloud
```

To check that Ollama is running and the model is available:

```bash
curl http://localhost:11434/api/tags
```

### 3 — Verify Ollama model

```bash
ollama pull gemma4:31b-cloud   # or whichever model you configured
ollama list                     # confirm it appears
```

---

## Running the Full Pipeline

The pipeline has three steps. If you already have the `data/features/` folder from this repo (committed), you can skip straight to **Step 3**.

---

### Step 1 — Crawl & download brochures

#### ICICI Prudential (targeted crawler with Akamai bypass)

```bash
python -m crawler.ipru_targeted
```

This will:
- Fetch the active products list from iciciprulife.com
- Cross-verify against any existing files in `data/raw/ICICI_Prudential/`
- Download only active-product brochures (skips withdrawn products)
- Save PDFs to `data/raw/ICICI_Prudential/`

#### Any other insurer (generic BFS crawler)

```bash
python -m crawler.main --company "HDFC Life" --url https://www.hdfclife.com
```

---

### Step 2 — Classify & process PDFs into structured format

#### ICICI Pru (rule-based, no LLM needed)

```bash
python process_ipru_raw.py
```

Dry-run first to preview what will be created:

```bash
python process_ipru_raw.py --dry-run
```

This copies PDFs to `data/processed/ICICI Prudential Life Insurance/<type>/` and writes a `.metadata.json` sidecar for each one.

#### Other insurers (LLM-based classifier)

```bash
python -m classifier.pipeline
```

---

### Step 3 — Run the RAG ingestion pipeline

This is the main indexing step. It reads every PDF in `data/processed/`, runs LLM feature extraction, embeds the text, and upserts everything into ChromaDB.

#### Index ICICI Pru products only

```bash
python -m rag.pipeline --company "ICICI Prudential"
```

#### Index all available insurers

```bash
python -m rag.pipeline
```

#### Force re-index (overwrite existing feature files and vectors)

```bash
python -m rag.pipeline --company "ICICI Prudential" --reindex
```

#### Preview only — no writes

```bash
python -m rag.pipeline --dry-run
```

**What happens during indexing:**

For each PDF the pipeline:
1. Extracts full text (all pages) via PyMuPDF
2. Calls Ollama 8 times **in parallel** (one per taxonomy section) to extract 50 structured fields
3. Saves the result as `data/features/<company>/<stem>.features.json`
4. Chunks the text into overlapping 1,000-char windows
5. Embeds each chunk with `all-MiniLM-L6-v2`
6. Upserts embeddings + metadata into ChromaDB

**Speed:** ~6.6 sec per PDF (8 parallel Ollama calls vs ~60 sec sequential).

---

### Step 4 — Launch the UI

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

The UI presents 8 questions covering the user's financial goal, risk appetite, investment horizon, dependents, liquidity needs, health risk concerns, premium preference, and maturity expectation. On submit it:

1. Maps answers to a weighted feature profile (no LLM call — instant)
2. Scores all ICICI Pru products against the profile
3. Applies a 25% boost for products matching the recommended plan type
4. Displays the top 5 matches with scores, dimension charts, and feature pills

---

## The 8 Questions (Profile Mapper)

| # | Question | Internal key | Options |
|---|----------|-------------|---------|
| 1 | Financial goal | `q1_goal` | `protect_family`, `wealth_growth`, `retirement`, `child_future` |
| 2 | Risk appetite | `q2_risk` | `conservative`, `moderate`, `aggressive`, `capital_safe` |
| 3 | Investment horizon | `q3_horizon` | `under_5`, `5_to_10`, `10_to_20`, `20_plus` |
| 4 | Dependents | `q4_dependents` | `spouse`, `children`, `parents`, `none` (multi-select) |
| 5 | Liquidity need | `q5_liquidity` | `anytime`, `after_5_years`, `none` |
| 6 | Health/accident risk | `q6_health_risk` | `critical_illness`, `accident`, `both`, `neither` |
| 7 | Premium pay mode | `q7_pay_mode` | `single`, `limited`, `regular`, `monthly` |
| 8 | Maturity expectation | `q8_maturity` | `rop`, `income`, `lump_sum`, `legacy` |

---

## The Feature Taxonomy (50 Fields)

Features are extracted by the LLM across 8 focused section prompts:

| Section | Fields | Examples |
|---------|--------|---------|
| Identity | 6 | product_name, product_type, UIN, is_linked |
| Eligibility | 10 | min/max entry age, policy term, sum assured, premium modes |
| Death Benefit | 6 | benefit type, income payout, terminal illness, increasing cover |
| Returns | 11 | guaranteed returns, IRR projections, loyalty additions, capital guarantee |
| Flexibility | 10 | partial withdrawal, SWP, fund switching, premium holiday |
| Riders | 7 | critical illness, accidental death, disability, waiver of premium |
| Charges | 4 | premium allocation %, fund management %, admin charge |
| Special | 3 | claim settlement ratio, NRI eligible, bancassurance |

---

## Scoring Logic

```
User answers
    │
    ▼
profile_mapper.py
  → Builds a weight vector over all 50 features
  → Applies goal / risk / dependent / liquidity / health multipliers
  → Normalises weights to sum = 1
    │
    ▼
scorer.py  (per product)
  → Maps each raw feature value → 0.0 / 0.5 / 1.0
  → Multiplies by feature weight
  → Sums → total_score (0–100)
  → Hard filters (e.g. conservative → exclude ULIPs)
  → Dimension scores (protection / returns / flexibility / riders / eligibility / charges)
    │
    ▼
ranker.py
  → Scores all 68 IPru products
  → Deduplicates by product name
  → Sorts descending
    │
    ▼
app.py
  → 25% boost for products matching the recommended plan type
  → Normalises top result to 100 for display
  → Renders cards with score bars, dimension charts, feature pills
```

**Hard filter examples:**

| User selection | Excluded products |
|---------------|------------------|
| Risk = Conservative | All ULIPs (`is_linked = True`) |
| Maturity = Return of Premium | Products without `return_of_premium = True` |
| Maturity = Income | Products without `income_payout_option = True` |
| Premium = Single lump sum | Products that don't support single pay mode |

---

## Known Issues & Notes

- **ICICI Pru website requires Akamai bypass** — standard `requests`/`aiohttp` return 403. `crawler/ipru_targeted.py` uses `curl_cffi` with `impersonate="chrome120"` to spoof Chrome's TLS fingerprint. Do not replace with standard HTTP libraries.
- **Ollama must be running** before the RAG pipeline or feature extraction is invoked. The UI itself requires no Ollama — it only reads from pre-computed `data/features/` JSON files.
- **`data/chroma/` is not committed** — the vector index is rebuilt locally by running `rag/pipeline.py`. The feature JSONs (`data/features/`) are committed and checked in, so you can run the UI without re-indexing.
- **Some feature fields are null for many products** — ICICI Pru brochures don't always state entry age explicitly. Scoring handles nulls gracefully (null = 0 contribution, doesn't break ranking).

---

## Quick Start (If `data/features/` Already Exists)

If you cloned this repo and the feature JSONs are already present (they are on the `rag` branch), you can skip the crawl and RAG steps and go straight to the UI:

```bash
git clone https://github.com/Rutvik0003/IPRU_Chatbot.git
cd IPRU_Chatbot
git checkout rag

pip install -r requirements.txt
cp .env.example .env         # Ollama not needed just for UI

streamlit run app.py
```

Open **http://localhost:8501**. Answer the 8 questions. See your top ICICI Pru products.

---

## Full Re-Run (From Scratch)

```bash
# 1. Crawl ICICI Pru active products
python -m crawler.ipru_targeted

# 2. Classify and write metadata sidecars
python process_ipru_raw.py

# 3. Index into ChromaDB + extract features (needs Ollama running)
python -m rag.pipeline --company "ICICI Prudential"

# 4. Launch UI
streamlit run app.py
```

---

## Contributors

- **Team Kappa** — ICICI Prudential Life Insurance internship project

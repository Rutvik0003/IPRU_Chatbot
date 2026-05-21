# Insurance PDF Scraper Pipeline

A production-grade crawler that scrapes insurance brochure PDFs from insurer websites
and organises them into company-named folders — ready for RAG ingestion.

---

## Features

- **Deep crawl** — follows internal links up to a configurable depth
- **JS-rendered pages** — Playwright headless browser fallback for SPAs
- **Smart PDF detection** — finds PDFs in `<a>`, `<iframe>`, `<embed>`, `<object>` tags
- **Retry logic** — exponential back-off on network errors (via Tenacity)
- **Deduplication** — skips already-downloaded files; hash-suffixes collisions
- **Parallel scraping** — optional multi-worker mode for faster runs
- **Structured output** — JSON results + log file after every run
- **Configurable** — per-company depth/page/delay overrides in `config.yaml`

---

## Project Structure

```
insurance_scraper/
├── scraper.py        # Core: crawl + download logic for one company
├── pipeline.py       # Orchestrator: multi-company, parallel, CLI
├── config.yaml       # Company list with optional per-company settings
├── requirements.txt  # Python dependencies
├── README.md
└── downloads/        # Created at runtime
    ├── HDFC Life/
    │   ├── brochure_term_plan.pdf
    │   └── ...
    ├── LIC India/
    └── ...
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Add companies to `config.yaml`

```yaml
companies:
  - name: "HDFC Life"
    url: "https://www.hdfclife.com"

  - name: "Your Company"
    url: "https://www.yourcompany.com"
    max_depth: 4      # optional override
    max_pages: 300    # optional override
```

---

## Usage

### Scrape all companies in config.yaml

```bash
python pipeline.py
```

### Quick single-company run (no config needed)

```bash
python pipeline.py --company "HDFC Life" --url https://www.hdfclife.com
```

### Parallel scraping (3 companies at once)

```bash
python pipeline.py --workers 3
```

### Custom output directory

```bash
python pipeline.py --output-dir /data/insurance_pdfs
```

### All CLI options

```
--config         Path to YAML config (default: config.yaml)
--company        Single company name
--url            Homepage URL for --company
--output-dir     Root folder for downloads (default: downloads/)
--workers        Number of parallel workers (default: 1)
--max-depth      Crawl depth from homepage (default: 3)
--max-pages      Max pages to visit per company (default: 200)
--delay          Seconds between requests (default: 0.5)
--no-playwright  Disable headless browser fallback
--no-skip-existing  Re-download already-existing PDFs
--verbose        Debug-level logging
```

---

## Output

### Folder structure

```
downloads/
└── HDFC Life/
    ├── term_insurance_brochure.pdf
    ├── ulip_plan_brochure.pdf
    └── ...
```

### JSON results (`downloads/results_YYYYMMDD_HHMMSS.json`)

```json
[
  {
    "company": "HDFC Life",
    "homepage": "https://www.hdfclife.com",
    "pdf_urls_found": 42,
    "downloaded": 38,
    "skipped": 4,
    "failed": 0,
    "files": ["downloads/HDFC Life/term_plan.pdf", ...]
  }
]
```

### Console summary

```
=================================================================
                      SCRAPING SUMMARY
=================================================================
Company                         Found    DL  Skip  Fail
-----------------------------------------------------------------
HDFC Life                          42    38     4     0
LIC India                          91    89     2     0
...
-----------------------------------------------------------------
TOTAL                             133   127     6     0
=================================================================
```

---

## Tips for Production

| Concern | Recommendation |
|---|---|
| Rate limiting | Increase `--delay` (e.g. `1.5`) or reduce `--workers` |
| Blocked by WAF | Playwright fallback is auto-enabled; rotate User-Agent if needed |
| Very large sites | Increase `--max-pages` (e.g. `500`) and `--max-depth 4` |
| Scheduling | Wrap in a cron job or Airflow DAG; `--no-skip-existing` to refresh |
| RAG ingestion | Point your loader at `downloads/<CompanyName>/` folders |

---

## Adding to a RAG Pipeline

After scraping, load PDFs with LangChain or LlamaIndex:

```python
from langchain_community.document_loaders import PyPDFDirectoryLoader

loader = PyPDFDirectoryLoader("downloads/HDFC Life/")
docs = loader.load()
```

Or iterate all companies:

```python
from pathlib import Path

for company_dir in Path("downloads").iterdir():
    if company_dir.is_dir():
        loader = PyPDFDirectoryLoader(str(company_dir))
        docs = loader.load()
        # ... chunk, embed, upsert to vector store
```

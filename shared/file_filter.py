import re

PRIORITY_KEYWORDS = [

    # Core Insurance
    "insurance",
    "insured",
    "insurer",
    "policy",
    "coverage",
    "cover",
    "premium",
    "sum-insured",
    "sum-assured",

    # Document Types
    "brochure",
    "policy-wording",
    "policywording",
    "claim-form",
    "claim",
    "proposal-form",
    "benefit-illustration",
    "benefits",
    "plan-details",

    # Health Insurance
    "health",
    "mediclaim",
    "hospital",
    "cashless",
    "critical-illness",
    "critical-care",
    "family-floater",
    "pre-existing",
    "wellness",

    # Life / Term
    "life",
    "term",
    "ulip",
    "retirement",
    "pension",
    "child-plan",
    "protection-plan",

    # Motor
    "motor",
    "car",
    "vehicle",
    "bike",
    "two-wheeler",
    "four-wheeler",
    "commercial-vehicle",

    # Travel
    "travel",
    "trip",
    "international",
    "student-travel",

    # Product Naming Style
    "secure",
    "shield",
    "protect",
    "protection",
    "care",
    "assure",
    "assured",
    "plus",
    "prime",
    "elite",
    "smart",
    "advantage",
    "max",
    "complete",
    "active",
    "essential",
    "supreme",

    # Insurance Terms
    "deductible",
    "copay",
    "co-pay",
    "waiting-period",
    "renewal",
    "rider",
    "add-on",
    "no-claim-bonus",
    "ncb",
    "hospitalization",
    "outpatient",
    "daycare",

    # Common Product Words
    "optima",
    "healthline",
    "healthcare",
    "protect360",
    "guaranteed",
    "income-plan",
    "wealth",
    "smart-care",
    "super-topup",
    "top-up"
]

REJECT_KEYWORDS = [

    # Finance / Investor
    "annual",
    "quarterly",
    "financial",
    "finance",
    "investor",
    "shareholder",
    "earnings",
    "revenue",
    "profit",
    "loss",
    "ebitda",
    "balance-sheet",
    "balance_sheet",
    "cashflow",
    "results",
    "presentation",
    "investor-presentation",
    "investor_deck",

    # Governance / Compliance
    "governance",
    "board",
    "committee",
    "compliance",
    "audit",
    "agm",
    "egm",
    "minutes",
    "resolution",
    "circular",
    "notification",

    # ESG / CSR
    "esg",
    "csr",
    "sustainability",
    "environment",
    "climate",

    # Legal
    "privacy",
    "privacy-policy",
    "terms",
    "terms-and-conditions",
    "legal",
    "agreement",
    "contract",
    "nda",
    "disclaimer",

    # Procurement / Vendor
    "tender",
    "rfp",
    "rfq",
    "procurement",
    "vendor",
    "quotation",

    # Tax
    "gst",
    "tax",
    "tds",
    "invoice",

    # HR / Careers
    "career",
    "jobs",
    "hiring",
    "recruitment",
    "internship",

    # Media / PR
    "press",
    "press-release",
    "media",
    "news",
    "advertisement",
    "campaign",

    # Misc Corporate
    "certificate",
    "licensing",
    "license",
    "broking",
    "share",
    "stock",
    "exchange",
    "memorandum",
    "moa",
    "aoa",
    "prospectus",
    "whitepaper",
    "white-paper",

    # Technical / Random
    "api",
    "documentation",
    "manual",
    "technical",
    "developer",
    "guide",

    # Banking / Non Insurance
    "loan",
    "credit-card",
    "mutual-fund",
    "demat",
    "fixed-deposit",
    "fd",
    "savings-account"
    "fy"
    'form'
    "consolidated"
    'Request'
    'Intimation'
    'voting'
    'transcription'
    'form'
]


def normalize(text):

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return text


def should_reject_file(
    filename
):

    filename = normalize(
        filename
    )

    for keyword in REJECT_KEYWORDS:

        if keyword in filename:

            return True

    return False


def is_priority_insurance_file(
    filename
):

    filename = normalize(
        filename
    )

    for keyword in PRIORITY_KEYWORDS:

        if keyword in filename:

            return True

    return False
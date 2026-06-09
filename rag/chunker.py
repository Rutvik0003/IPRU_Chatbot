import re

SECTION_PATTERNS = [
    re.compile(r"^[A-Z][A-Z\s\-&/]{4,}$", re.MULTILINE),   # ALL CAPS headers
    re.compile(r"^\d+\.\s+[A-Z]", re.MULTILINE),            # 1. Numbered
    re.compile(r"^[IVX]+\.\s+", re.MULTILINE),               # Roman numerals
]

INSURANCE_SECTIONS = [
    "eligibility", "benefits", "death benefit", "premium", "riders",
    "exclusion", "maturity", "surrender", "charges", "terms and conditions",
    "features", "plan details", "fund options", "partial withdrawal",
    "critical illness", "claim", "tax benefit",
]


def _find_section_label(text_before: str) -> str:
    for section in INSURANCE_SECTIONS:
        if section in text_before.lower()[-200:]:
            return section
    return "general"


def chunk_text(
    text: str,
    chunk_words: int = 350,
    overlap_words: int = 40,
) -> list[dict]:
    """
    Split text into overlapping word-count chunks with a best-effort
    section label. Returns list of {text, index, section, word_count}.
    """
    # Collapse excessive whitespace but keep paragraph breaks
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    idx = 0

    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunk_words_slice = words[start:end]
        chunk_text_str = " ".join(chunk_words_slice)

        section = _find_section_label(" ".join(words[max(0, start - 50):start]))

        chunks.append({
            "text": chunk_text_str,
            "index": idx,
            "section": section,
            "word_count": len(chunk_words_slice),
        })

        idx += 1
        start += chunk_words - overlap_words

    return chunks

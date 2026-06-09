"""
LLM-based feature extraction via Ollama.

Why LLM here and NOWHERE else:
  Insurance brochures express the same fact in dozens of different ways.
  "Entry age: 18-65 years" and "You must be at least 18 and not yet 66"
  both mean min_entry_age=18, max_entry_age=65. Regex cannot handle this.
  The LLM grounds every answer to the text you give it — if it's not there,
  the answer is null. That's the entire contract.

Speed: all 8 section calls run concurrently (asyncio.gather).
Accuracy: each section receives a front+tail text window so information
  buried at the end of a brochure (charges, exclusions, riders) is not cut off.
"""

import asyncio
import json
import os
import re

import aiohttp

from scoring.taxonomy import FEATURE_TAXONOMY, SECTIONS

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
MAX_RETRIES  = 3

# ---------------------------------------------------------------------------
# Text windows — how much of the document each section sees.
# front_chars + tail_chars are concatenated with a "[...]" separator.
# ---------------------------------------------------------------------------
_WINDOWS: dict[str, tuple[int, int]] = {
    "identity":     (4000, 0),      # always in first pages
    "eligibility":  (8000, 1000),   # mostly upfront, some in fine print
    "death_benefit":(8000, 2000),   # front summary + back conditions
    "returns":      (6000, 4000),   # benefit illustration often at the back
    "flexibility":  (6000, 3000),   # partial withdrawal / SWP rules vary
    "riders":       (5000, 4000),   # rider details frequently at the back
    "charges":      (2000, 6000),   # charge schedules are almost always at the end
    "special":      (4000, 3000),   # claim ratio / NRI clauses can be anywhere
}


def _build_text_window(full_text: str, section: str) -> str:
    front, tail = _WINDOWS.get(section, (6000, 2000))
    head = full_text[:front]
    if tail and len(full_text) > front + tail:
        end = full_text[-tail:]
        return head + "\n\n[...]\n\n" + end
    return head


SYSTEM_PROMPT = """You are an insurance document analyst. Extract specific fields from the provided brochure text.

Rules (follow exactly):
- Output ONLY valid JSON, no markdown, no explanation.
- Use null for any field not explicitly mentioned in the text.
- For boolean fields: true or false only.
- For numeric fields: extract the exact number as a number, not a string.
- For list fields: output a JSON array of strings.
- Never guess, infer, or hallucinate. Only extract what is written.
- If a field is "optional" or "available on request", use false (not inbuilt).
"""


SECTION_PROMPTS = {
    "identity": """Extract these identity fields from the text:
- product_name: full official product name (string)
- insurer: insurance company name (string)
- product_type: one of [term, ulip, savings, annuity, child, health, group] (string)
- uin_number: IRDAI UIN number if present (string or null)
- is_linked: true if market-linked ULIP, false if not (boolean)
- is_participating: true if participates in bonuses (boolean)

Return JSON with exactly these keys.""",

    "eligibility": """Extract these eligibility fields from the text:
- min_entry_age: minimum age in years to buy this policy (integer or null)
- max_entry_age: maximum age in years to buy this policy (integer or null)
- min_policy_term: minimum policy term in years (integer or null)
- max_policy_term: maximum policy term in years, or "whole_life" (number/string or null)
- whole_life_option: true if policy can cover till age 99/100 (boolean)
- min_sum_assured: minimum sum assured in INR (number or null)
- max_sum_assured: maximum sum assured in INR, or "no_limit" (number/string or null)
- min_annual_premium: minimum annual premium in INR (number or null)
- premium_pay_modes: list of supported modes, e.g. ["single","limited","regular"] (array)
- online_purchase: true if policy can be bought online without an agent (boolean)

Return JSON with exactly these keys.""",

    "death_benefit": """Extract these death benefit fields from the text:
- death_benefit_type: one of [lump_sum, income, combo] (string or null)
- income_payout_option: true if death benefit can be received as monthly income (boolean)
- income_payout_duration: number of years for income payout if applicable (integer or null)
- terminal_illness_inbuilt: true if terminal illness benefit is included WITHOUT paying extra (boolean)
- increasing_cover_option: true if sum assured can be increased over time (boolean)
- life_stage_enhancement: true if cover auto-increases on marriage, child birth, home purchase (boolean)

Return JSON with exactly these keys.""",

    "returns": """Extract these returns and savings fields from the text:
- guaranteed_returns: true if policy offers guaranteed non-market-linked returns (boolean)
- return_of_premium: true if all premiums are returned on maturity or survival (boolean)
- rop_percentage: percentage of premiums returned, e.g. 100, 110 (number or null)
- projected_irr_4pct: illustrated IRR at 4% fund return per IRDAI (number or null)
- projected_irr_8pct: illustrated IRR at 8% fund return per IRDAI (number or null)
- loyalty_additions: true if loyalty bonus is added to fund value (boolean)
- loyalty_addition_pct: loyalty addition as percentage of fund value (number or null)
- maturity_booster: true if an additional percentage is added at maturity (boolean)
- capital_guarantee: true if capital or premium is protected (boolean)
- capital_guarantee_pct: percentage of capital guaranteed (number or null)
- return_of_charges: true if premium allocation and mortality charges are returned at maturity (boolean)

Return JSON with exactly these keys.""",

    "flexibility": """Extract these flexibility fields from the text:
- partial_withdrawal: true if partial fund withdrawal is allowed (boolean)
- partial_withdrawal_min_years: minimum years before partial withdrawal is allowed (integer or null)
- systematic_withdrawal_plan: true if SWP facility is available (boolean)
- fund_switching: true if switching between investment funds is allowed (boolean)
- free_fund_switches: number of free switches per year, or "unlimited" (number/string or null)
- premium_holiday: true if premiums can be paused temporarily (boolean)
- premium_holiday_months: maximum months of premium holiday (integer or null)
- top_up_allowed: true if additional top-up premiums are accepted (boolean)
- portfolio_strategies: number of managed portfolio strategies offered (integer or null)
- loan_against_policy: true if a loan can be taken against the policy (boolean)

Return JSON with exactly these keys.""",

    "riders": """Extract these rider fields from the text:
- critical_illness_rider: true if a critical illness rider is available (boolean)
- ci_illnesses_covered: number of critical illnesses covered by the rider (integer or null)
- accidental_death_rider: true if accidental death benefit rider is available (boolean)
- disability_rider: true if total or partial disability rider is available (boolean)
- waiver_of_premium: true if premiums are waived on death or disability of the proposer (boolean)
- family_income_benefit: true if a monthly income is paid to the family on policyholder death (boolean)
- maternity_benefit: true if a maternity benefit rider is available (boolean)

Return JSON with exactly these keys.""",

    "charges": """Extract these charge fields from the text (especially for ULIP products):
- premium_allocation_charge_pct: premium allocation charge as percentage of premium (number or null)
- policy_admin_charge_monthly: monthly policy administration charge in INR (number or null)
- fund_management_charge_pct: fund management charge as annual percentage of fund value (number or null)
- mortality_charge_basis: how mortality charge is calculated, e.g. "per 1000 SA" (string or null)

Return JSON with exactly these keys.""",

    "special": """Extract these special fields from the text:
- claim_settlement_ratio: insurer's claim settlement ratio as a percentage (number or null)
- bancassurance_available: true if this policy is available through bank partners (boolean)
- nri_allowed: true if NRI customers can purchase this policy (boolean)

Return JSON with exactly these keys.""",
}


# ---------------------------------------------------------------------------
# Async Ollama call
# ---------------------------------------------------------------------------

async def _call_ollama_async(
    http: aiohttp.ClientSession,
    system: str,
    user: str,
) -> str:
    payload = {
        "model":   OLLAMA_MODEL,
        "messages": [
            {"role": "system",  "content": system},
            {"role": "user",    "content": user},
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 600,
        },
    }

    for attempt in range(MAX_RETRIES):
        try:
            async with http.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["message"]["content"]
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt
            print(f"  [extractor] Ollama retry {attempt+1} in {wait}s: {e}")
            await asyncio.sleep(wait)

    return ""


# ---------------------------------------------------------------------------
# Parsing & validation (unchanged)
# ---------------------------------------------------------------------------

def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def _validate(features: dict) -> dict:
    for field, value in list(features.items()):
        if value is None:
            continue
        meta = FEATURE_TAXONOMY.get(field, {})
        ftype = meta.get("type", "str")

        try:
            if ftype == "bool" and not isinstance(value, bool):
                features[field] = bool(value)
            elif ftype == "int" and not isinstance(value, int):
                features[field] = int(float(value))
            elif ftype == "float" and not isinstance(value, float):
                features[field] = float(value)
            elif ftype == "list" and isinstance(value, str):
                features[field] = [value]

            if field in ("min_entry_age", "max_entry_age"):
                if not (1 <= features[field] <= 120):
                    features[field] = None
            if field in ("claim_settlement_ratio",):
                if not (0 <= features[field] <= 100):
                    features[field] = None
            if field in ("projected_irr_4pct", "projected_irr_8pct"):
                if not (0 <= features[field] <= 50):
                    features[field] = None

        except (TypeError, ValueError):
            features[field] = None

    return features


def _merge(sections: list[dict]) -> dict:
    merged: dict = {}
    for section_data in sections:
        for field, value in section_data.items():
            if value is None:
                merged.setdefault(field, None)
                continue
            existing = merged.get(field)
            if existing is None:
                merged[field] = value
            elif field.startswith("min_"):
                try:
                    merged[field] = min(float(existing), float(value))
                except (TypeError, ValueError):
                    pass
            elif field.startswith("max_"):
                try:
                    merged[field] = max(float(existing), float(value))
                except (TypeError, ValueError):
                    pass
    return merged


# ---------------------------------------------------------------------------
# Public async entry point
# ---------------------------------------------------------------------------

async def extract_features(full_text: str, metadata: dict) -> dict:
    """
    Run all 8 section extractions concurrently, merge, validate, attach _meta.
    Returns the complete features dict ready for storage.
    """
    product = metadata.get("product_name", "?")
    print(f"[extractor] {product} — running {len(SECTIONS)} sections in parallel")

    async with aiohttp.ClientSession() as http:

        async def _run_section(section_name: str) -> dict:
            text_window = _build_text_window(full_text, section_name)
            prompt = SECTION_PROMPTS[section_name]
            user_msg = (
                f"{prompt}\n\n"
                f"Brochure text:\n---\n{text_window}\n---\n\n"
                f"Return JSON only."
            )
            try:
                raw = await _call_ollama_async(http, SYSTEM_PROMPT, user_msg)
                result = _parse_json(raw)
                return _validate(result)
            except Exception as e:
                print(f"  [extractor] section '{section_name}' failed: {e}")
                return {}

        section_results = await asyncio.gather(
            *[_run_section(s) for s in SECTIONS],
            return_exceptions=False,
        )

    merged = _merge(list(section_results))

    merged["_meta"] = {
        "company":          metadata.get("company", ""),
        "insurance_type":   metadata.get("insurance_type", ""),
        "document_type":    metadata.get("document_type", ""),
        "product_name":     metadata.get("product_name", ""),
        "source_file":      metadata.get("source_file", ""),
        "processed_at":     metadata.get("processed_at", ""),
        "extraction_model": OLLAMA_MODEL,
    }

    return merged

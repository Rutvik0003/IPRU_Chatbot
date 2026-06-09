import os
import json
import re
import time

import requests
from dotenv import load_dotenv

from classifier.schemas import (
    InsuranceDocument
)

load_dotenv()

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


SYSTEM_PROMPT = """
You are an insurance document classifier.

Analyze the provided PDF text.

Return ONLY valid JSON.

You MUST return ALL fields.

Schema:

{
    "is_insurance_document": true,
    "document_type": "brochure",
    "insurance_type": "health",
    "company": "company name",
    "product_name": "product name",
    "confidence": 0.95
}

Possible document_type:
- brochure
- policy_wording
- claim_form
- annual_report
- disclosure
- tax_document
- advertisement
- other

Possible insurance_type:
- health
- term
- life
- motor
- travel
- investment
- unknown
"""

MAX_RETRIES = 2


def extract_json(text):

    # Remove markdown blocks
    text = re.sub(
        r"```json|```",
        "",
        text
    ).strip()

    # Extract JSON object
    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if not match:

        return {}

    json_str = match.group()

    try:

        return json.loads(
            json_str
        )

    except Exception as e:

        print(
            f"JSON parse failed: {e}"
        )

        return {}


def call_llm(text):

    for attempt in range(
        MAX_RETRIES
    ):

        try:

            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": text[:10000]
                        }
                    ],
                    "format": "json",
                    "stream": False,
                    "options": {
                        "temperature": 0,
                        "num_predict": 300,
                    },
                },
                timeout=90,
            )

            response.raise_for_status()

            return (
                response.json()
                ["message"]
                ["content"]
            )

        except Exception as e:

            print(
                f"\nAttempt "
                f"{attempt+1} failed:"
            )

            print(str(e))

            if attempt < MAX_RETRIES - 1:

                time.sleep(
                    2 ** attempt
                )

            else:

                raise e

    raise Exception(
        "Max retries exceeded"
    )


def classify_document(text):

    try:

        content = call_llm(text)

        print(
            "\n========== RAW LLM OUTPUT =========="
        )

        print(content)

        print(
            "====================================\n"
        )

        data = extract_json(
            content
        )

        # -------------------------
        # SANITIZE MODEL OUTPUT
        # -------------------------

        if not isinstance(data, dict):

            data = {}

        # Boolean
        if data.get(
            "is_insurance_document"
        ) is None:

            data[
                "is_insurance_document"
            ] = False

        # Document type
        if (
            data.get("document_type")
            is None
        ):

            data[
                "document_type"
            ] = "other"

        # Insurance type
        if (
            data.get("insurance_type")
            is None
        ):

            data[
                "insurance_type"
            ] = "unknown"

        # Company
        if (
            data.get("company")
            is None
        ):

            data[
                "company"
            ] = "unknown"

        # Product
        if (
            data.get("product_name")
            is None
        ):

            data[
                "product_name"
            ] = "unknown"

        # Confidence
        if (
            data.get("confidence")
            is None
        ):

            data[
                "confidence"
            ] = 0.0


        # Safety fallback
        if not data:

            print(
                "Empty JSON returned "
                "by model"
            )

            return InsuranceDocument()

        return InsuranceDocument(
            **data
        )

    except Exception as e:

        print(
            f"Classification failed: {e}"
        )

        return InsuranceDocument(
            is_insurance_document=False,
            document_type="other",
            insurance_type="unknown",
            company="unknown",
            product_name="unknown",
            confidence=0.0
        )
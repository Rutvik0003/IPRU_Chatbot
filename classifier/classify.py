import os
import json
import re

from dotenv import load_dotenv
from openai import OpenAI

from classifier.schemas import (
    InsuranceDocument
)

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


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


def extract_json(text):

    # Remove markdown json blocks
    text = re.sub(
        r"```json|```",
        "",
        text
    ).strip()

    # Extract first JSON object
    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if not match:
        return {}

    json_str = match.group()

    try:

        return json.loads(json_str)

    except Exception as e:

        print(
            f"JSON parse failed: {e}"
        )

        return {}


def classify_document(text):

    try:

        response = client.chat.completions.create(

            model="deepseek/deepseek-v4-flash:free",

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": text[:12000]
                }
            ],

            temperature=0
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        print(
            "\n========== RAW LLM OUTPUT =========="
        )

        print(content)

        print(
            "====================================\n"
        )

        data = extract_json(content)

        return InsuranceDocument(**data)

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
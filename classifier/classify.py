import os
import json
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

from classifier.schemas import (
    InsuranceDocument
)

load_dotenv()

client = OpenAI(
    api_key=os.getenv(
        "OPENROUTER_API_KEY"
    ),
    base_url=(
        # "https://generativelanguage.googleapis.com/v1beta/openai/"
        'https://openrouter.ai/api/v1/'
    )
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


MODEL_NAME = (
    # "gemini-2.5-flash"
    'openai/gpt-oss-120b:free'
    # "deepseek/deepseek-v4-flash:free"
)

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

            response = (
                client.chat.completions.create(

                    model=MODEL_NAME,

                    response_format={
                        "type": "json_object"
                    },


                    messages=[
                        {
                            "role": "system",
                            "content": (
                                SYSTEM_PROMPT
                            )
                        },
                        {
                            "role": "user",
                            "content": (
                                text[:10000]
                            )
                        }
                    ],

                    temperature=0
                )
            )

            return (
                response
                .choices[0]
                .message
                .content
            )

        except Exception as e:

            error_str = str(e)

            print(
                f"\nAttempt "
                f"{attempt+1} failed:"
            )

            print(error_str)

            # Handle rate limits
            if "429" in error_str:

                wait_time = (
                    2 ** attempt
                )

                print(
                    f"Rate limited. "
                    f"Waiting "
                    f"{wait_time}s..."
                )

                time.sleep(
                    wait_time
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
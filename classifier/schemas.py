from pydantic import BaseModel


class InsuranceDocument(BaseModel):

    is_insurance_document: bool = False

    document_type: str = "other"

    insurance_type: str = "unknown"

    company: str = "unknown"

    product_name: str = "unknown"

    confidence: float = 0.0
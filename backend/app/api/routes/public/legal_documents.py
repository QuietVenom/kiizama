from fastapi import APIRouter

from app.features.legal_documents import (
    PUBLIC_SIGNUP_LEGAL_DOCUMENTS,
    PUBLIC_SIGNUP_SIMPLIFIED_NOTICE,
)
from app.models import LegalDocumentPublic, PublicLegalDocuments

router = APIRouter(prefix="/public/legal-documents", tags=["public-legal-documents"])


@router.get("/", response_model=PublicLegalDocuments)
def list_public_legal_documents() -> PublicLegalDocuments:
    documents = [
        LegalDocumentPublic(
            type=document.type,
            title=document.title,
            url=document.url,
            version=document.version,
            required=document.required,
        )
        for document in PUBLIC_SIGNUP_LEGAL_DOCUMENTS
    ]
    return PublicLegalDocuments(
        simplified_notice=PUBLIC_SIGNUP_SIMPLIFIED_NOTICE,
        documents=documents,
    )

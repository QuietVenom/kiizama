from dataclasses import dataclass
from typing import Final, Literal

LegalDocumentType = Literal["privacy_notice", "terms_conditions"]
LegalAcceptanceSource = Literal["public_signup"]

PUBLIC_SIGNUP_LEGAL_ACCEPTANCE_SOURCE: Final[LegalAcceptanceSource] = "public_signup"
PUBLIC_SIGNUP_SIMPLIFIED_NOTICE: Final[str] = (
    "Para crear tu cuenta, necesitas leer y aceptar la documentación legal "
    "aplicable. Puedes revisar cada documento en una nueva pestaña antes de "
    "continuar."
)


@dataclass(frozen=True)
class LegalDocumentDefinition:
    type: LegalDocumentType
    title: str
    url: str
    version: str
    required: bool = True


PUBLIC_SIGNUP_LEGAL_DOCUMENTS: Final[tuple[LegalDocumentDefinition, ...]] = (
    LegalDocumentDefinition(
        type="privacy_notice",
        title="Aviso de Privacidad",
        url="/privacy",
        version="v1.0",
    ),
    LegalDocumentDefinition(
        type="terms_conditions",
        title="Términos y Condiciones",
        url="/terms-conditions",
        version="v1.0",
    ),
)

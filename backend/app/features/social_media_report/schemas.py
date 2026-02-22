from pydantic import BaseModel, Field, model_validator


class InstagramReportRequest(BaseModel):
    """Payload para generar reportes de Instagram."""

    usernames: list[str] = Field(
        ...,
        description="Lista de usernames a usar para generar los reportes (max 20).",
        min_length=1,
        max_length=20,
    )
    template_name: str = Field(
        default="social_media_report.html",
        description="Nombre de la plantilla a renderizar.",
    )
    generate_html: bool = Field(
        default=True,
        description="Indica si debe generarse el HTML como parte del proceso.",
    )
    generate_pdf: bool = Field(
        default=False,
        description="Indica si debe generarse un PDF a partir del HTML.",
    )

    @model_validator(mode="after")
    def validate_request(self) -> "InstagramReportRequest":
        if not self.usernames:
            raise ValueError(
                "Debe proporcionar al menos un username para generar el reporte."
            )
        if len(self.usernames) > 20:
            raise ValueError("Se permite un maximo de 20 usernames por solicitud.")
        if not self.generate_html and not self.generate_pdf:
            raise ValueError("Debe solicitar al menos un formato (HTML o PDF).")
        return self


class InstagramReportResponse(BaseModel):
    """Metadatos del reporte generado (descarga directa en el endpoint)."""

    filenames: list[str] = Field(default_factory=list)


__all__ = ["InstagramReportRequest", "InstagramReportResponse"]

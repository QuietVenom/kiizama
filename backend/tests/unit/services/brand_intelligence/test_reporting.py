import pytest

from app.features.brand_intelligence.services.service_reporting import (
    generate_report_files,
)


class FakeReportGenerator:
    def __init__(
        self,
        *,
        html: str = "<html>report</html>",
        pdf: bytes | None = b"%PDF",
        batch_pdf: list[bytes] | None = None,
    ) -> None:
        self.html = html
        self.pdf = pdf
        self.batch_pdf = batch_pdf
        self.html_calls: list[dict[str, str]] = []
        self.pdf_calls: list[dict[str, str]] = []
        self.batch_calls: list[list[str]] = []

    def generate_html(self, context):
        self.html_calls.append(dict(context))
        return self.html

    def generate_pdf(self, context):
        self.pdf_calls.append(dict(context))
        return self.pdf

    def generate_pdfs_from_html_batch(self, html_documents: list[str]) -> list[bytes]:
        self.batch_calls.append(html_documents)
        return self.batch_pdf if self.batch_pdf is not None else [b"%PDF-from-html"]


@pytest.mark.anyio
async def test_report_files_html_only_returns_html_file() -> None:
    # Arrange
    generator = FakeReportGenerator(html="<html>brand</html>")

    # Act
    files = await generate_report_files(
        confirmation_template_name="campaign.html",
        context={"brand_name": "Acme"},
        generate_html=True,
        generate_pdf=False,
        generator=generator,
    )

    # Assert
    assert [file.filename for file in files] == ["campaign.html"]
    assert files[0].content_type == "text/html; charset=utf-8"
    assert files[0].content == b"<html>brand</html>"
    assert generator.html_calls == [{"brand_name": "Acme"}]
    assert generator.batch_calls == []
    assert generator.pdf_calls == []


@pytest.mark.anyio
async def test_report_files_pdf_only_uses_generate_pdf() -> None:
    # Arrange
    generator = FakeReportGenerator(pdf=b"%PDF-only")

    # Act
    files = await generate_report_files(
        confirmation_template_name="creator.html",
        context={"creator_username": "creator_one"},
        generate_html=False,
        generate_pdf=True,
        generator=generator,
    )

    # Assert
    assert [file.filename for file in files] == ["creator.pdf"]
    assert files[0].content_type == "application/pdf"
    assert files[0].content == b"%PDF-only"
    assert generator.pdf_calls == [{"creator_username": "creator_one"}]
    assert generator.html_calls == []
    assert generator.batch_calls == []


@pytest.mark.anyio
async def test_report_files_pdf_generation_empty_batch_raises_value_error() -> None:
    # Arrange
    generator = FakeReportGenerator(html="<html>brand</html>", batch_pdf=[])

    # Act / Assert
    with pytest.raises(ValueError, match="No se pudo generar el PDF"):
        await generate_report_files(
            confirmation_template_name="campaign.html",
            context={"brand_name": "Acme"},
            generate_html=True,
            generate_pdf=True,
            generator=generator,
        )


@pytest.mark.anyio
async def test_report_files_pdf_generation_none_result_raises_value_error() -> None:
    # Arrange
    generator = FakeReportGenerator(pdf=None)

    # Act / Assert
    with pytest.raises(ValueError, match="No se pudo generar el PDF"):
        await generate_report_files(
            confirmation_template_name="creator.html",
            context={"creator_username": "creator_one"},
            generate_html=False,
            generate_pdf=True,
            generator=generator,
        )

import json
from collections import UserDict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.features.general.types import profile_picture
from app.features.general.types.html_pdf_report_generator import HtmlPdfReportGenerator


class FakeImageResponse:
    headers = {"Content-Type": "image/png; charset=utf-8"}

    def __enter__(self) -> "FakeImageResponse":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

    def read(self) -> bytes:
        return b"image-bytes"


class FakePdfPage:
    def __init__(
        self,
        dimensions: dict[str, Any] | None = None,
        *,
        measurement_error: Exception | None = None,
    ) -> None:
        self.dimensions = dimensions or {"width": 96, "height": 96}
        self.measurement_error = measurement_error
        self.content: str | None = None
        self.pdf_kwargs: dict[str, Any] | None = None

    def set_content(self, html_content: str, *, wait_until: str) -> None:
        self.content = html_content
        self.wait_until = wait_until

    def evaluate(self, script: str) -> dict[str, Any]:
        del script
        if self.measurement_error is not None:
            raise self.measurement_error
        return self.dimensions

    def pdf(self, **kwargs: Any) -> bytes:
        self.pdf_kwargs = kwargs
        return b"%PDF"


def test_profile_picture_resolves_allowed_https_cdn_to_data_uri(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        profile_picture,
        "urlopen",
        lambda *_args, **_kwargs: FakeImageResponse(),
    )

    data_uri = profile_picture.resolve_profile_picture_data_uri(
        "https://images.cdninstagram.com/profile.jpg"
    )

    assert data_uri == "data:image/png;base64,aW1hZ2UtYnl0ZXM="


def test_enrich_profile_picture_blocks_untrusted_url() -> None:
    profile = {"profile_pic_url": "http://example.com/profile.jpg"}

    profile_picture.enrich_profile_picture(profile)

    assert profile["profile_pic_url"] == ""
    assert "profile_pic_src" not in profile


def test_html_pdf_report_generator_renders_html_and_uses_pdf_batch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    template = tmp_path / "report.html"
    template.write_text("<h1>{{ title }}</h1>", encoding="utf-8")
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )
    monkeypatch.setattr(
        generator,
        "generate_pdfs_from_html_batch",
        lambda html: [f"PDF:{html[0]}".encode()],
    )

    html = generator.generate_html(SimpleNamespace(model_dump=lambda: {"title": "Hi"}))
    pdf = generator.generate_pdf({"title": "Hi"})

    assert html == "<h1>Hi</h1>"
    assert pdf == b"PDF:<h1>Hi</h1>"


def test_html_pdf_report_generator_loads_json_file(tmp_path: Path) -> None:
    # Arrange
    data_path = tmp_path / "report.json"
    data_path.write_text(json.dumps({"title": "Loaded"}), encoding="utf-8")
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )

    # Act
    data = generator.load_data(str(data_path))

    # Assert
    assert data == {"title": "Loaded"}


def test_html_pdf_report_generator_build_context_handles_mapping_model_dump_and_unknown(
    tmp_path: Path,
) -> None:
    # Arrange
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )
    model = SimpleNamespace(model_dump=lambda: {"title": "Model"})

    # Act / Assert
    assert generator.build_context(UserDict({"title": "Mapping"})) == {
        "title": "Mapping"
    }
    assert generator.build_context(model) == {"title": "Model"}
    assert generator.build_context(object()) == {}


def test_html_pdf_report_generator_writes_html_output_file(tmp_path: Path) -> None:
    # Arrange
    template = tmp_path / "report.html"
    output_path = tmp_path / "out" / "report.html"
    template.write_text("<h1>{{ title }}</h1>", encoding="utf-8")
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )

    # Act
    html = generator.generate_html({"title": "Saved"}, output_path=str(output_path))

    # Assert
    assert html == "<h1>Saved</h1>"
    assert output_path.read_text(encoding="utf-8") == "<h1>Saved</h1>"


def test_html_pdf_report_generator_writes_pdf_output_file_and_returns_none(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Arrange
    template = tmp_path / "report.html"
    output_path = tmp_path / "out" / "report.pdf"
    template.write_text("<h1>{{ title }}</h1>", encoding="utf-8")
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )
    monkeypatch.setattr(
        generator,
        "generate_pdfs_from_html_batch",
        lambda _html: [b"%PDF-saved"],
    )

    # Act
    result = generator.generate_pdf({"title": "Saved"}, output_path=str(output_path))

    # Assert
    assert result is None
    assert output_path.read_bytes() == b"%PDF-saved"


def test_html_pdf_report_generator_generates_html_and_pdf_batches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Arrange
    template = tmp_path / "report.html"
    template.write_text("<h1>{{ title }}</h1>", encoding="utf-8")
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )
    monkeypatch.setattr(
        generator,
        "generate_pdfs_from_html_batch",
        lambda html_documents: [f"PDF:{html}".encode() for html in html_documents],
    )

    # Act
    html_documents = generator.generate_html_batch([{"title": "One"}, {"title": "Two"}])
    pdf_documents = generator.generate_pdfs_batch([{"title": "One"}, {"title": "Two"}])

    # Assert
    assert html_documents == ["<h1>One</h1>", "<h1>Two</h1>"]
    assert pdf_documents == [b"PDF:<h1>One</h1>", b"PDF:<h1>Two</h1>"]


def test_html_pdf_report_generator_measures_document_dimensions(
    tmp_path: Path,
) -> None:
    # Arrange
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )
    page = FakePdfPage({"width": 192, "height": 96})

    # Act
    width_in, height_in = generator._measure_document_inches(page)

    # Assert
    assert width_in == 2.0
    assert height_in == 1.0


def test_html_pdf_report_generator_measurement_failure_falls_back_to_a4(
    tmp_path: Path,
) -> None:
    # Arrange
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )
    page = FakePdfPage(measurement_error=RuntimeError("browser failed"))

    # Act
    pdf_bytes = generator._render_pdf_bytes(page, "<main>Report</main>")

    # Assert
    assert pdf_bytes == b"%PDF"
    assert page.content == "<main>Report</main>"
    assert page.pdf_kwargs is not None
    assert page.pdf_kwargs["format"] == "A4"
    assert page.pdf_kwargs["prefer_css_page_size"] is True


def test_html_pdf_report_generator_invalid_dimensions_fall_back_to_a4(
    tmp_path: Path,
) -> None:
    # Arrange
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="report.html",
    )

    for dimensions in (
        {"width": 0, "height": 120},
        {"width": 120, "height": "invalid"},
        {"width": 120},
    ):
        page = FakePdfPage(dimensions)

        # Act
        pdf_bytes = generator._render_pdf_bytes(page, "<main>Report</main>")

        # Assert
        assert pdf_bytes == b"%PDF"
        assert page.pdf_kwargs is not None
        assert page.pdf_kwargs["format"] == "A4"
        assert page.pdf_kwargs["prefer_css_page_size"] is True


def test_html_pdf_report_generator_empty_batch_returns_empty_list(
    tmp_path: Path,
) -> None:
    generator = HtmlPdfReportGenerator(
        template_path=str(tmp_path),
        template_name="missing.html",
    )

    assert generator.generate_pdfs_from_html_batch([]) == []

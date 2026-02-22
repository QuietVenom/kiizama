from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import Page, sync_playwright


class HtmlPdfReportGenerator:
    """Generic HTML/PDF report generator backed by Jinja and Playwright."""

    def __init__(self, template_path: str, template_name: str):
        self.template_path = template_path
        self.template_name = template_name
        self.env = Environment(
            loader=FileSystemLoader(template_path),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.logger = logging.getLogger(__name__)

    def load_data(self, data_source: str | dict[str, Any]) -> dict[str, Any]:
        """Load context data from a JSON file path or a dict."""
        if isinstance(data_source, str):
            with open(data_source, encoding="utf-8") as file:
                return cast(dict[str, Any], json.load(file))
        return data_source

    def build_context(self, data: Any) -> dict[str, Any]:
        """Hook for feature-specific context building."""
        if isinstance(data, dict):
            return data
        if isinstance(data, Mapping):
            return dict(data)
        if hasattr(data, "model_dump"):
            return cast(dict[str, Any], data.model_dump())
        return {}

    def generate_html(
        self,
        data: Any,
        output_path: str | None = None,
        template_name: str | None = None,
    ) -> str:
        """Render HTML using the configured template and context hook."""
        template = self.env.get_template(template_name or self.template_name)
        context = self.build_context(data)
        html_content = template.render(context)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(html_content)

        return html_content

    def generate_pdf(
        self,
        data: Any,
        output_path: str | None = None,
        template_name: str | None = None,
    ) -> bytes | None:
        """Generate PDF bytes from rendered HTML."""
        html_content = self.generate_html(data, template_name=template_name)
        pdf_bytes = self.generate_pdfs_from_html_batch([html_content])[0]

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(pdf_bytes)
            return None

        return pdf_bytes

    def generate_html_batch(
        self,
        reports_data: list[Any],
        template_name: str | None = None,
    ) -> list[str]:
        """Generate a batch of HTML documents in-memory."""
        return [
            self.generate_html(data, template_name=template_name)
            for data in reports_data
        ]

    def generate_pdfs_batch(
        self,
        reports_data: list[Any],
        template_name: str | None = None,
    ) -> list[bytes]:
        """Generate a batch of PDFs in-memory."""
        html_contents = self.generate_html_batch(
            reports_data,
            template_name=template_name,
        )
        return self.generate_pdfs_from_html_batch(html_contents)

    def generate_pdfs_from_html_batch(self, html_contents: list[str]) -> list[bytes]:
        """Convert multiple HTML strings to PDF bytes using one browser session."""
        if not html_contents:
            return []

        pdfs: list[bytes] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chromium")
            page = browser.new_page()
            page.emulate_media(media="print")
            for html_content in html_contents:
                pdfs.append(self._render_pdf_bytes(page, html_content))
            browser.close()
        return pdfs

    def _measure_document_inches(self, page: Page) -> tuple[float | None, float | None]:
        try:
            dimensions = page.evaluate(
                "() => ({"
                "  width: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth),"
                "  height: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
                "})"
            )
        except Exception as exc:  # pragma: no cover - defensive runtime fallback
            self.logger.debug("No se pudieron medir dimensiones del documento: %s", exc)
            return None, None

        try:
            width_px = float(dimensions["width"])
            height_px = float(dimensions["height"])
        except (KeyError, TypeError, ValueError):
            return None, None

        if width_px <= 0 or height_px <= 0:
            return None, None

        width_in = max(width_px / 96.0, 1.0)
        height_in = max(height_px / 96.0, 1.0)
        return width_in, height_in

    def _render_pdf_bytes(self, page: Page, html_content: str) -> bytes:
        page.set_content(html_content, wait_until="networkidle")

        width_in, height_in = self._measure_document_inches(page)
        pdf_kwargs: dict[str, Any] = {
            "print_background": True,
            "margin": {"top": "0", "right": "0", "bottom": "0", "left": "0"},
        }
        if width_in is not None and height_in is not None:
            pdf_kwargs["width"] = f"{width_in:.2f}in"
            pdf_kwargs["height"] = f"{height_in:.2f}in"
        else:
            pdf_kwargs["format"] = "A4"
            pdf_kwargs["prefer_css_page_size"] = True
        return page.pdf(**pdf_kwargs)


__all__ = ["HtmlPdfReportGenerator"]

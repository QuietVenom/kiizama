from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.features.general.types import HtmlPdfReportGenerator


@dataclass(frozen=True, slots=True)
class ReportFile:
    filename: str
    content_type: str
    content: bytes


async def generate_report_files(
    *,
    confirmation_template_name: str,
    context: Mapping[str, Any],
    generate_html: bool,
    generate_pdf: bool,
    generator: HtmlPdfReportGenerator,
) -> list[ReportFile]:
    files: list[ReportFile] = []
    base_name = Path(confirmation_template_name).stem

    html_content = ""
    if generate_html:
        html_content = await asyncio.to_thread(generator.generate_html, context)
        files.append(
            ReportFile(
                filename=confirmation_template_name,
                content_type="text/html; charset=utf-8",
                content=html_content.encode("utf-8"),
            )
        )

    if generate_pdf:
        if html_content:
            pdf_contents = await asyncio.to_thread(
                generator.generate_pdfs_from_html_batch,
                [html_content],
            )
            if not pdf_contents:
                raise ValueError("No se pudo generar el PDF del reporte.")
            pdf_bytes = pdf_contents[0]
        else:
            pdf_bytes = await asyncio.to_thread(generator.generate_pdf, context)
            if pdf_bytes is None:
                raise ValueError("No se pudo generar el PDF del reporte.")

        files.append(
            ReportFile(
                filename=f"{base_name}.pdf",
                content_type="application/pdf",
                content=pdf_bytes,
            )
        )

    return files


__all__ = ["ReportFile", "generate_report_files"]

import asyncio
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, cast

from anyio import to_thread
from sqlmodel import Session

from app.core.db import engine
from app.crud.profile_snapshots import list_profile_snapshots_full

from .schemas import InstagramReportRequest
from .types.instagram_report_generator import InstagramReportGenerator

# Configuración base de rutas
BASE_DIR = Path(__file__).resolve().parents[3]  # Raíz del proyecto backend
TEMPLATES_DIR = BASE_DIR / "app" / "features" / "templates" / "social_media_report"


@dataclass(frozen=True, slots=True)
class ReportFile:
    filename: str
    content_type: str
    content: bytes


def _list_report_snapshots(usernames: list[str]) -> list[dict[str, Any]]:
    with Session(engine) as session:
        return list_profile_snapshots_full(
            session,
            skip=0,
            limit=max(len(usernames), 1),
            usernames=usernames,
        )


async def generate_instagram_report(
    collection: Any,
    payload: InstagramReportRequest | dict[str, Any],
) -> list[ReportFile]:
    """Genera reportes de Instagram (HTML/PDF) desde snapshots persistidos."""
    del collection

    if isinstance(payload, dict):
        request = InstagramReportRequest(**payload)
    else:
        request = payload

    snapshots = await to_thread.run_sync(
        partial(_list_report_snapshots, request.usernames)
    )

    if not snapshots:
        raise LookupError(
            "No se encontraron snapshots para los usernames proporcionados."
        )

    snapshots_by_username: dict[str, list[Mapping[str, Any]]] = {}
    for snapshot_doc in snapshots:
        if not snapshot_doc:
            continue
        username = _extract_username(snapshot_doc)
        if not username:
            continue
        snapshots_by_username.setdefault(username, []).append(snapshot_doc)

    missing_usernames = [
        username
        for username in request.usernames
        if username not in snapshots_by_username
    ]
    if missing_usernames:
        raise LookupError(
            "No se encontraron snapshots para los usernames: "
            + ", ".join(missing_usernames)
        )

    generator = InstagramReportGenerator(
        template_path=str(TEMPLATES_DIR),
        template_name=request.template_name,
    )

    files: list[ReportFile] = []
    include_suffix = len(request.usernames) > len(set(request.usernames))
    report_jobs: list[tuple[str, dict[str, Any]]] = []

    for username in request.usernames:
        snapshot_list = snapshots_by_username.get(username)
        if not snapshot_list:
            raise LookupError(
                "No se encontraron snapshots para el username: " + username
            )
        snapshot = snapshot_list.pop(0)
        data = _snapshot_to_report_data(snapshot)
        snapshot_id = str(snapshot.get("_id") or "")
        base_name = _build_base_name(username, snapshot_id, include_suffix)
        report_jobs.append((base_name, data))

    reports_data = [data for _, data in report_jobs]

    html_contents: list[str] = []
    pdf_contents: list[bytes] = []

    if request.generate_html:
        html_contents = await asyncio.to_thread(
            generator.generate_html_batch,
            reports_data,
        )

    if request.generate_pdf:
        if html_contents:
            pdf_contents = await asyncio.to_thread(
                generator.generate_pdfs_from_html_batch,
                html_contents,
            )
        else:
            pdf_contents = await asyncio.to_thread(
                generator.generate_pdfs_batch,
                reports_data,
            )

    for index, (base_name, _) in enumerate(report_jobs):
        if request.generate_html:
            html_content = html_contents[index]
            files.append(
                ReportFile(
                    filename=f"{base_name}.html",
                    content_type="text/html; charset=utf-8",
                    content=html_content.encode("utf-8"),
                )
            )

        if request.generate_pdf:
            if index >= len(pdf_contents) or not pdf_contents[index]:
                raise ValueError("No se pudo generar el PDF del reporte.")
            files.append(
                ReportFile(
                    filename=f"{base_name}.pdf",
                    content_type="application/pdf",
                    content=pdf_contents[index],
                )
            )

    return files


def _snapshot_to_report_data(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    snapshot_data = _coerce_mapping(snapshot)
    profile = _coerce_mapping(snapshot_data.get("profile"))
    if not profile:
        raise ValueError("El snapshot no contiene información de perfil.")

    posts_docs = _coerce_list(snapshot_data.get("posts"))
    posts: list[Any] = []
    for doc in posts_docs:
        doc_data = _coerce_mapping(doc)
        posts.extend(_coerce_list(doc_data.get("posts")))

    reels_docs = _coerce_list(snapshot_data.get("reels"))
    reels: list[Any] = []
    for doc in reels_docs:
        doc_data = _coerce_mapping(doc)
        reels.extend(_coerce_list(doc_data.get("reels")))

    username = str(profile.get("username") or "")
    profile_url = f"https://www.instagram.com/{username}/" if username else None

    return {
        "scrape": {
            "user": profile,
            "posts": posts,
            "reels": reels,
            "recommended_users": [],
            "ai_categories": _coerce_list(profile.get("ai_categories")),
            "ai_roles": _coerce_list(profile.get("ai_roles")),
        },
        "profile_url": profile_url,
    }


def _extract_username(snapshot: Mapping[str, Any]) -> str:
    profile = _coerce_mapping(snapshot.get("profile"))
    return str(profile.get("username") or "")


def _build_base_name(username: str, snapshot_id: str, include_suffix: bool) -> str:
    base = _safe_slug(username) or "report"
    if include_suffix:
        base = f"{base}_{snapshot_id}"
    return base


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return cast(dict[str, Any], value.model_dump())
    return {}


def _coerce_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_slug(value: str | None) -> str:
    if not value:
        return ""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return slug.lower()


__all__ = ["generate_instagram_report", "ReportFile"]

from collections.abc import Awaitable, Callable
from typing import Any

from app.features.social_media_report.service import ReportFile


async def generated_html_report(*_: Any, **__: Any) -> list[ReportFile]:
    return [
        ReportFile(
            filename="alpha.html",
            content=b"<html><body>alpha</body></html>",
            content_type="text/html",
        )
    ]


async def noop_async(*_: Any, **__: Any) -> None:
    return None


def noop(*_: Any, **__: Any) -> None:
    return None


AsyncCallable = Callable[..., Awaitable[Any]]

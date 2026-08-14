"""Jinja HTML rendering and async-safe WeasyPrint PDF conversion."""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

_windows_dll_handle: Any | None = None
if sys.platform == "win32" and "WEASYPRINT_DLL_DIRECTORIES" not in os.environ:
    # Current WeasyPrint requires a modern Pango runtime. MSYS2 is its documented
    # Windows installation route; deployments can override this directory explicitly.
    msys2_runtime = Path("C:/msys64/mingw64/bin")
    if msys2_runtime.exists():
        os.environ["WEASYPRINT_DLL_DIRECTORIES"] = str(msys2_runtime)
        # Windows can otherwise resolve an older GTK Pango from PATH before the
        # directory advertised to WeasyPrint. Keep the handle alive for the process.
        os.environ["PATH"] = f"{msys2_runtime}{os.pathsep}{os.environ['PATH']}"
        _windows_dll_handle = os.add_dll_directory(str(msys2_runtime))

from weasyprint import HTML  # type: ignore[import-untyped]

from app.reports.context_builder import ReportContext

TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"


def _percent(value: Decimal | float | None) -> str:
    return "—" if value is None else f"{float(value):.2%}"


def _inr(value: Decimal | float | None) -> str:
    return "—" if value is None else f"₹{float(value):,.2f}"


def _number(value: Decimal | float | None, digits: int = 4) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}"


def create_template_environment() -> Environment:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIRECTORY),
        autoescape=select_autoescape(("html", "jinja")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters.update(percent=_percent, inr=_inr, number=_number)
    return environment


def render_html(
    template_name: str,
    context: ReportContext,
    *,
    environment: Environment | None = None,
) -> str:
    """Render a report template; exposed separately for deterministic template tests."""

    selected = environment or create_template_environment()
    return selected.get_template(template_name).render(
        report=context,
        report_data=asdict(context),
    )


def _write_pdf(html: str) -> bytes:
    result: Any = HTML(string=html, base_url=str(TEMPLATE_DIRECTORY)).write_pdf()
    if not isinstance(result, bytes):
        raise TypeError("WeasyPrint did not return PDF bytes")
    return result


async def render_pdf(template_name: str, context: ReportContext) -> bytes:
    """Render PDF bytes without blocking the asyncio event loop."""

    html = render_html(template_name, context)
    return await asyncio.to_thread(_write_pdf, html)

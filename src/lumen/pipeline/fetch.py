"""Fetch HTML and extract main text with trafilatura."""

from __future__ import annotations

import re

import httpx
import trafilatura

from lumen.config import get_settings

_MAX_BYTES = 1_500_000


def fetch_url(url: str) -> str:
    """Return cleaned plain text for a single URL."""
    settings = get_settings()
    headers = {"User-Agent": settings.lumen_http_user_agent}
    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        timeout=settings.lumen_fetch_timeout_seconds,
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        raw = resp.content
        if len(raw) > _MAX_BYTES:
            raw = raw[:_MAX_BYTES]
        html = raw.decode(resp.encoding or "utf-8", errors="replace")

    extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
    text = extracted or ""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

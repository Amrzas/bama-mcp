"""Shared HTTP client for bama.ir internal APIs. Swappable transport for tests."""

from __future__ import annotations

import os

import httpx

BASE = "https://bama.ir"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}
TIMEOUT = 10  # fail fast instead of hanging (VPN/SSL issues)

_transport: httpx.BaseTransport | None = None


def set_transport(transport: httpx.BaseTransport | None) -> None:
    """Override the HTTP transport (tests inject httpx.MockTransport). None = real network."""
    global _transport
    _transport = transport


def get(path: str, params: dict | None = None, accept: str = "application/json") -> httpx.Response:
    """GET path (e.g. '/cad/api/search?...') against BASE. Raises on HTTP/network errors."""
    kwargs: dict = {"timeout": TIMEOUT}
    proxy = os.environ.get("BAMA_MCP_PROXY")
    if proxy:
        kwargs["proxy"] = proxy
    if _transport is not None:
        kwargs["transport"] = _transport
    with httpx.Client(base_url=BASE, headers={**HEADERS, "Accept": accept}, **kwargs) as c:
        r = c.get(path, params=params)
        r.raise_for_status()
        return r

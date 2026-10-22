"""Shared HTTP client for bama.ir internal APIs. Swappable transport for tests."""

from __future__ import annotations

import atexit
import os

import httpx

BASE = "https://bama.ir"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}
TIMEOUT = 10  # fail fast instead of hanging (VPN/SSL issues)

_transport: httpx.BaseTransport | None = None
_client: httpx.Client | None = None


def _build_client() -> httpx.Client:
    kwargs: dict = {"timeout": TIMEOUT, "limits": httpx.Limits(max_keepalive_connections=4)}
    proxy = os.environ.get("BAMA_MCP_PROXY")
    if proxy:
        kwargs["proxy"] = proxy
    if _transport is not None:
        kwargs["transport"] = _transport
    return httpx.Client(base_url=BASE, headers=HEADERS, **kwargs)


def close() -> None:
    """Drop the pooled client (next call reconnects)."""
    global _client
    if _client is not None and not _client.is_closed:
        _client.close()
    _client = None


atexit.register(close)


def set_transport(transport: httpx.BaseTransport | None) -> None:
    """Override the HTTP transport (tests inject httpx.MockTransport). None = real network."""
    global _transport
    close()
    _transport = transport


def get(path: str, params: dict | None = None, accept: str = "application/json") -> httpx.Response:
    """GET path (e.g. '/cad/api/search?...') against BASE. Raises on HTTP/network errors.

    One pooled client is reused for the whole process, so repeat calls skip the TLS
    handshake (~0.32s -> ~0.15s per request against bama.ir).
    """
    global _client
    if _client is None or _client.is_closed:
        _client = _build_client()
    r = _client.get(path, params=params, headers={"Accept": accept})
    r.raise_for_status()
    return r

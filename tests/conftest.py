import json
from pathlib import Path

import httpx
import pytest

from bama_mcp import catalog, http

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def api(monkeypatch):
    """Fake upstream: api["/path"] = JSON body. Unknown paths return 404.

    Caches are reset per test so fixture swaps take effect.
    """
    catalog.reset_caches()

    class Routes(dict):
        calls: list[httpx.Request]

    routes = Routes()
    routes.calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        routes.calls.append(request)
        target = routes.get(request.url.path)
        if target is None:
            return httpx.Response(404, json={"error": "no fake route"})
        if callable(target):
            return target(request)  # type: ignore[return-value]
        return httpx.Response(200, json=target)

    http.set_transport(httpx.MockTransport(handler))
    yield routes
    http.set_transport(None)
    catalog.reset_caches()

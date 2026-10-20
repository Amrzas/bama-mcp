"""Live tests against the real bama.ir API. Run: pytest -m live (needs an Iranian IP)."""

import pytest

from bama_mcp import http as bama_http
from bama_mcp import server

pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def real_network():
    """Disable the offline fake upstream for live tests."""
    bama_http.set_transport(None)
    yield


def test_search_returns_items():
    result = server.search_cars(vehicle="peugeot", page_size=5)
    assert "error" not in result, result
    assert result["items"]
    first = result["items"][0]
    assert first["url"].startswith("https://bama.ir/")
    assert first["price_fa"]


def test_list_brands_nonempty():
    out = server.list_brands()
    assert len(out) > 50


def test_list_models_peugeot():
    out = server.list_models("peugeot")
    assert any("206" in m["title_fa"] for m in out)


def test_city_filter_restricts_results():
    # 'تهران' matches the whole province (includes ورامین etc.); use a unique city name.
    result = server.search_cars(vehicle="peugeot", city="تبریز", page_size=10)
    assert "error" not in result, result
    assert result["items"]
    assert all((i["location"] or "").startswith("تبریز") for i in result["items"])


def test_car_details_end_to_end():
    search = server.search_cars(vehicle="peugeot", page_size=1)
    url = search["items"][0]["url"]
    details = server.car_details(url)
    assert "error" not in details, details
    assert details["name"]

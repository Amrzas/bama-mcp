"""Offline tests against recorded bama.ir responses (no network)."""

import httpx
from conftest import fixture

from bama_mcp import server
from bama_mcp.format import price_fa

mcp = server.mcp


def test_price_fa_formats():
    assert price_fa(410_000_000) == "۴۱۰ میلیون تومان"
    assert price_fa(4_100_000_000) == "۴.۱ میلیارد تومان"
    assert price_fa(4_000_000_000) == "۴ میلیارد تومان"
    assert price_fa(None) == "توافقی"
    assert price_fa(0) == "توافقی"
    assert price_fa(500, "negotiable") == "توافقی"


def test_search_cars_basic(api):
    api["/cad/api/search"] = fixture("search_peugeot.json")
    result = server.search_cars(vehicle="peugeot")
    assert result["items"], "expected items"
    first = result["items"][0]
    assert first["summary_fa"] and first["price_fa"]
    assert first["url"].startswith("https://bama.ir/car/detail-")
    sent = api.calls[0].url
    assert "vehicle=peugeot" in str(sent)


def test_search_cars_city_resolves_region(api):
    api["/gen/api/filters/region"] = fixture("filter_region.json")
    api["/cad/api/search"] = fixture("search_206_tehran.json")
    result = server.search_cars(vehicle="peugeot,206ir", city="تهران", sort=4)
    assert result["items"]
    region_sent = [c for c in api.calls if "region=" in str(c.url)]
    assert region_sent, "expected region param"
    assert all(i["location"].startswith("تهران") for i in result["items"])


def test_search_cars_unknown_city(api):
    api["/gen/api/filters/region"] = fixture("filter_region.json")
    result = server.search_cars(city="شهری که وجود ندارد")
    assert result["error"] == "unknown_city"


def test_search_cars_havaleh_dropped_by_default(api):
    api["/cad/api/search"] = fixture("search_peugeot.json")
    result = server.search_cars(vehicle="peugeot", include_havaleh=False)
    assert not any("حواله" in (i["title"] or "") for i in result["items"])


def test_search_cars_timeout_is_actionable(api):
    def boom(request):
        raise httpx.ReadTimeout("nope")

    api["/cad/api/search"] = boom
    result = server.search_cars(vehicle="peugeot")
    assert result["error"] == "bama_timeout"
    assert "VPN" in result["hint"]


def test_search_cars_price_max_filters(api):
    api["/cad/api/search"] = fixture("search_peugeot.json")
    unfiltered = server.search_cars(vehicle="peugeot")
    capped = server.search_cars(vehicle="peugeot", price_max=1_000_000_000)
    assert len(capped["items"]) <= len(unfiltered["items"])
    assert all(i["price_toman"] <= 1_000_000_000 for i in capped["items"])


def _ad(code: str, price: int | None, title: str = "پژو ۲۰۶ تیپ ۲") -> dict:
    return {
        "type": "ad",
        "detail": {
            "code": code,
            "title": title,
            "subtitle": "مدل ۱۳۹۰",
            "year": "۱۳۹۰",
            "mileage": "۲۰۰,۰۰۰ کیلومتر",
            "location": "مشهد/مشهد",
            "url": f"/car/detail-{code}",
        },
        "price": {"price": price, "type": "negotiable" if price is None else "fixed"},
    }


def _page(ads: list[dict], total_pages: int = 1, total_count: int | None = None) -> dict:
    return {
        "metadata": {"total_pages": total_pages, "total_count": total_count or len(ads)},
        "data": {"ads": ads},
    }


def test_search_cars_fetches_all_pages_until_empty(api):
    pages = {
        "0": _page([_ad("a1", 300_000_000), _ad("a2", 320_000_000)], total_pages=5),
        "1": _page([_ad("a3", 340_000_000), _ad("a4", 360_000_000)], total_pages=5),
        "2": _page([], total_pages=5),
    }
    api["/cad/api/search"] = lambda r: httpx.Response(
        200, json=pages.get(r.url.params["pageIndex"], _page([], total_pages=5))
    )
    result = server.search_cars(vehicle="peugeot,206ir", sort=4)
    assert result["pages_fetched"] == 3
    assert len(result["items"]) == 4
    assert result["truncated"] is False


def test_search_cars_early_stop_at_price_max(api):
    """sort=4 + price_max: once a page holds an ad past the cap, no later page is fetched."""

    def responder(request):
        idx = request.url.params["pageIndex"]
        if idx == "0":
            return httpx.Response(
                200, json=_page([_ad("b1", 900_000_000), _ad("b2", 1_200_000_000)], total_pages=9)
            )
        if idx == "1":
            return httpx.Response(
                200, json=_page([_ad("b3", 1_400_000_000), _ad("b4", 1_600_000_000)], total_pages=9)
            )
        raise AssertionError(f"page {idx} should not be fetched after passing price_max")

    api["/cad/api/search"] = responder
    result = server.search_cars(vehicle="peugeot,206ir", sort=4, price_max=1_500_000_000)
    assert result["pages_fetched"] == 2
    assert len(result["items"]) == 3
    assert all(i["price_toman"] <= 1_500_000_000 for i in result["items"])


def test_search_cars_no_early_stop_without_price_cap(api):
    """sort=4 alone must keep paging through expensive ads."""
    pages = {
        "0": _page([_ad("d1", 2_000_000_000)], total_pages=3),
        "1": _page([_ad("d2", 2_500_000_000)], total_pages=3),
        "2": _page([], total_pages=3),
    }
    api["/cad/api/search"] = lambda r: httpx.Response(
        200, json=pages.get(r.url.params["pageIndex"], _page([], total_pages=3))
    )
    result = server.search_cars(vehicle="peugeot", sort=4)
    assert result["pages_fetched"] == 3
    assert len(result["items"]) == 2


def test_search_cars_truncated_when_max_pages_hit(api):
    api["/cad/api/search"] = lambda r: httpx.Response(
        200, json=_page([_ad("c" + r.url.params["pageIndex"], 300_000_000)], total_pages=7)
    )
    result = server.search_cars(vehicle="peugeot", max_pages=2)
    assert result["pages_fetched"] == 2
    assert result["truncated"] is True
    # caller can continue from where we stopped
    assert result["page"] + result["pages_fetched"] == 2


def test_search_cars_url_and_code_always_present(api):
    """Even the leanest `fields` request keeps the ad link click-able."""
    api["/cad/api/search"] = fixture("search_peugeot.json")
    result = server.search_cars(vehicle="peugeot", fields="title")
    assert all(set(i) == {"title", "code", "url"} for i in result["items"])
    assert all(i["url"] and i["url"].startswith("https://bama.ir/") for i in result["items"])


def test_search_cars_default_fields_are_compact(api):
    api["/cad/api/search"] = fixture("search_peugeot.json")
    result = server.search_cars(vehicle="peugeot")
    item = result["items"][0]
    assert {"code", "title", "summary_fa", "price_toman", "price_fa", "location", "year", "url"} <= set(item)
    assert "dealer" not in item and "image" not in item and "subtitle" not in item


def test_search_cars_unknown_field_lists_available(api):
    api["/cad/api/search"] = fixture("search_peugeot.json")
    result = server.search_cars(vehicle="peugeot", fields="title,nonsense")
    assert result["error"] == "unknown_field"
    assert "nonsense" in result["unknown_fields"]
    assert "price_fa" in result["available_fields"]


def test_search_cars_fields_star_returns_all(api):
    api["/cad/api/search"] = fixture("search_peugeot.json")
    result = server.search_cars(vehicle="peugeot", fields="*")
    assert "dealer" in result["items"][0] and "subtitle" in result["items"][0]


def test_search_cars_limit_stops_fetching(api):
    """limit items collected => no further pages fetched."""
    ads = [_ad(f"e{n}", 300_000_000 + n * 10_000_000) for n in range(10)]
    pages = {
        "0": _page(ads[:3], total_pages=5),
        "1": _page(ads[3:6], total_pages=5),
        "2": _page(ads[6:9], total_pages=5),
    }

    def responder(request):
        idx = request.url.params["pageIndex"]
        if idx not in pages:
            raise AssertionError(f"page {idx} should not be fetched once limit is reached")
        return httpx.Response(200, json=pages[idx])

    api["/cad/api/search"] = responder
    result = server.search_cars(vehicle="peugeot,206ir", sort=4, limit=5, page_size=3)
    # limit is respected up to page granularity: 2 pages of 3 ads = 6 items
    assert len(result["items"]) == 6
    assert result["truncated"] is True


def test_car_details_requires_full_url():
    result = server.car_details("pmsqbaqe")
    assert result["error"] == "code_only_not_supported_yet"


def test_car_details_parses_ld_json(api, tmp_path):
    html = """<html><head>
    <script type="application/ld+json">{"@type":"Car","name":"پژو، 207","url":"https://bama.ir/car/detail-x",
    "brand":{"name":"پژو"},"productionDate":1403,"color":"سفید","vehicleTransmission":"اتوماتیک",
    "fuelType":"بنزینی","bodyType":"hatchback","vehicleEngine":{"engineDisplacement":{"value":1.6}}}</script>
    </head><body><img src="https://cdn-sth1.bama.ir/uploads/BamaImages/VehicleCarImages/a/CarImage_abc_thumb.jpg?x-img=v1"></body></html>"""
    api["/car/detail-x"] = lambda r: httpx.Response(200, text=html)
    result = server.car_details("https://bama.ir/car/detail-x")
    assert result["name"] == "پژو، 207"
    assert result["transmission"] == "اتوماتیک"
    assert result["engine_liter"] == 1.6
    assert result["images"]


def test_list_brands(api):
    api["/cad/api/filter/vehicle"] = fixture("filter_vehicle.json")
    out = server.list_brands()
    assert out
    assert all("title_fa" in b and "value" in b for b in out)


def test_list_models(api):
    api["/cad/api/filter/vehicle"] = fixture("filter_vehicle.json")
    out = server.list_models("peugeot")
    assert out
    assert all(m["value"].startswith("peugeot") for m in out)


def test_list_cities(api):
    api["/gen/api/filters/region"] = fixture("filter_region.json")
    out = server.list_cities()
    assert out
    assert all(c["kind"] in ("state", "city") for c in out)


def test_all_tools_exist():
    import asyncio

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {"search_cars", "car_details", "list_brands", "list_cities", "list_models"}

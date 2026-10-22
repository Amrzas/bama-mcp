"""Bama.ir MCP server — search cars and get ad details. No API key needed."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

import httpx
from fastmcp import FastMCP

from bama_mcp import http
from bama_mcp.catalog import brands, cities, models, reset_caches, resolve_city
from bama_mcp.format import ad_to_item, is_havaleh, parse_price_toman

mcp = FastMCP("bama")


ALL_FIELDS = [
    "code", "title", "subtitle", "summary_fa", "brand", "brand_fa", "year", "mileage",
    "location", "time", "body_status", "transmission", "fuel", "color", "price_type",
    "price_toman", "price_fa", "dealer", "seller_type", "image", "url",
]
DEFAULT_FIELDS = [
    "code", "title", "summary_fa", "price_toman", "price_fa", "location", "year",
    "mileage", "transmission", "fuel", "seller_type", "url",
]


@mcp.tool
def search_cars(
    vehicle: str = "",
    sort: int = 0,
    page: int = 0,
    page_size: int = 12,
    price_min: int = 0,
    price_max: int = 0,
    include_havaleh: bool = False,
    city: str = "",
    max_pages: int = 10,
    limit: int = 30,
    fields: str = "",
) -> dict[str, Any]:
    """Search car ads on bama.ir. Returns ready-to-link items — every item has 'url'.

    vehicle: brand/model filter, e.g. 'peugeot' or 'peugeot,207' (from list_brands/list_models).
    sort: 0=default, 2=newest-update, 3=most expensive, 4=cheapest, 5=newest year, 6=oldest year, 7=lowest mileage.
    page: zero-based page index to start from. page_size: 1-30 (bama API rejects larger).
    max_pages: pages fetched per call, 1-20 (default 10). Fetching stops as soon as 'limit'
      items are collected, when results end, or when a sort=4 search passes price_max
      (sort=3 passes price_min) — those price-bounded results are usually complete in one call.
    limit: max items returned, 1-30 (default 30; may exceed by at most one page). If
      'truncated' is true, call again with page = page + pages_fetched to get the next chunk.
    fields: comma-separated list to control the output and token cost.
      Default (compact, ~12 fields): code, title, summary_fa, price_toman, price_fa,
      location, year, mileage, transmission, fuel, seller_type, url.
      'fields=title,url' for the leanest output; 'fields=*' for all 21 fields.
      'code' and 'url' are always included.
    price_min/price_max: filter by price in Toman (0 = no limit). Applied client-side.
    include_havaleh: False (default) drops 'حواله' (installment-slip) ads whose
      price is a down-payment, not the car price. True keeps them.
    city: city name in Persian or English (e.g. 'تهران', 'مشهد', 'tehran').
      Whole state if only state matches. Use list_cities for all names.
    summary_fa is a ready Persian one-liner for tables; price_fa ('۴۱۰ میلیون تومان').
    Priceless/negotiable ads sink to the bottom when sorting by price.
    """
    page_size = max(1, min(page_size, 30))
    max_pages = max(1, min(max_pages, 20))
    limit = max(1, min(limit, 30))
    page_size = min(page_size, limit)  # never fetch more ads per page than we will return

    requested = [f.strip() for f in (fields or "").split(",") if f.strip()]
    if requested and requested[0] in ("*", "all"):
        requested = list(ALL_FIELDS)
    unknown = [f for f in requested if f not in ALL_FIELDS]
    if unknown:
        return {
            "error": "unknown_field",
            "unknown_fields": unknown,
            "available_fields": ALL_FIELDS,
        }
    keep = set(requested) if requested else set(DEFAULT_FIELDS)
    keep |= {"code", "url"}  # the ad link is never dropped

    base = []
    if vehicle:
        base.append(f"vehicle={quote(vehicle, safe='')}")
    if city:
        resolved = resolve_city(city)
        if resolved is None:
            return {"error": "unknown_city", "hint": f"city '{city}' not found — call list_cities for valid names"}
        base.append(f"region={quote(resolved, safe='')}")
    if sort:
        base.append(f"sort={sort}")

    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}
    pages_fetched = 0
    stopped_early = False
    reached_end = False
    limit_hit = False
    try:
        for p in range(page, page + max_pages):
            query = "&".join(base + [f"pageIndex={p}", f"pageSize={page_size}"])
            data = http.get(f"/cad/api/search?{query}").json()
            pages_fetched += 1
            meta = data.get("metadata", {}) or {}
            ads = [a for a in (data.get("data", {}) or {}).get("ads", []) if a.get("type") == "ad"]
            if not ads:
                reached_end = True
                break
            page_items = [ad_to_item(a) for a in ads]
            # ascending sort (4) passed the cap, or descending (3) passed the floor:
            # everything after this page is outside the bound anyway.
            bound_passed = False
            if sort == 4 and price_max and any(
                i["price_toman"] and i["price_toman"] > price_max for i in page_items
            ):
                bound_passed = True
            if sort == 3 and price_min and any(
                i["price_toman"] and i["price_toman"] < price_min for i in page_items
            ):
                bound_passed = True
            for it in page_items:
                key = it.get("code") or it.get("url")
                if key and key in seen:
                    continue
                if not include_havaleh and is_havaleh(it):
                    continue
                if price_max and (not it["price_toman"] or it["price_toman"] > price_max):
                    continue
                if price_min and (not it["price_toman"] or it["price_toman"] < price_min):
                    continue
                if key:
                    seen.add(key)
                items.append(it)
            if bound_passed:
                stopped_early = True
                break
            total_pages = meta.get("total_pages")
            if total_pages is not None and p + 1 >= total_pages:
                reached_end = True
                break
            if len(items) >= limit:
                limit_hit = True
                break
    except httpx.TimeoutException:
        return {
            "error": "bama_timeout",
            "hint": "bama.ir did not answer in 10s — check VPN is OFF (bama blocks foreign IPs). Or set BAMA_MCP_PROXY.",
        }
    except httpx.HTTPError as e:
        return {"error": "bama_request_failed", "hint": str(e)[:200]}

    if sort in (3, 4):
        items.sort(
            key=lambda i: (i["price_toman"] is None, i["price_toman"] or 0),
            reverse=(sort == 3),
        )
    if keep != set(ALL_FIELDS):
        items = [{k: i.get(k) for k in ALL_FIELDS if k in keep} for i in items]
    total_pages = meta.get("total_pages")
    truncated = (
        not (stopped_early or reached_end)
        and (limit_hit or (total_pages is not None and page + pages_fetched < total_pages))
    )
    return {
        "total_count": meta.get("total_count"),
        "total_pages": total_pages,
        "page": page,
        "pages_fetched": pages_fetched,
        "limit": limit,
        "truncated": truncated,
        "items": items,
    }


@mcp.tool
def car_details(code_or_url: str) -> dict[str, Any]:
    """Get full details of one ad. Pass the ad 'url' field from search_cars (a full https://bama.ir/car/detail-... link)."""
    if not code_or_url.startswith("http"):
        return {"error": "code_only_not_supported_yet", "hint": "pass the full ad URL (url field from search_cars)"}
    url = code_or_url
    try:
        html = http.get(url.replace("https://bama.ir", ""), accept="text/html").text
    except httpx.TimeoutException:
        return {"error": "bama_timeout", "hint": "bama.ir did not answer in 10s — check VPN is OFF"}
    except httpx.HTTPError as e:
        return {"error": "bama_request_failed", "hint": str(e)[:200]}
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if not m:
        return {"error": "details_not_found", "url": url}
    ld = json.loads(m.group(1))
    imgs = sorted(
        set(
            re.findall(
                r'https://cdn-sth1\.bama\.ir/uploads/BamaImages/VehicleCarImages/[^"\s]+?\.jpg[^"\s]*',
                html,
            )
        )
    )
    phone = re.search(r"(09\d{9})", html)
    return {
        "name": ld.get("name"),
        "brand": (ld.get("brand") or {}).get("name"),
        "price_toman": parse_price_toman(str(ld.get("offers", {}).get("price") or ""))
        if ld.get("offers")
        else None,
        "year": ld.get("productionDate"),
        "color": ld.get("color"),
        "interior_color": ld.get("vehicleInteriorColor"),
        "transmission": ld.get("vehicleTransmission"),
        "fuel": ld.get("fuelType"),
        "body_type": ld.get("bodyType"),
        "engine_liter": ((ld.get("vehicleEngine") or {}).get("engineDisplacement") or {}).get("value"),
        "description": ld.get("description"),
        "images": imgs[:10],
        "seller_phone": phone.group(1) if phone else None,
        "url": ld.get("url", url),
    }


@mcp.tool
def list_brands() -> list[dict[str, str]]:
    """List all car brands on bama.ir with Farsi names. Returns 'value' to use in search_cars/list_models."""
    return brands()


@mcp.tool
def list_cities() -> list[dict[str, str]]:
    """List all states and cities on bama.ir with Persian names. Pass title_fa to search_cars city param."""
    return cities()


@mcp.tool
def list_models(brand: str) -> list[dict[str, str]]:
    """List models of a brand. brand = value from list_brands (e.g. 'peugeot'). Returns 'value' for search_cars vehicle param."""
    return models(brand)


def main() -> None:
    reset_caches()
    mcp.run()


if __name__ == "__main__":
    main()

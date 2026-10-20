"""Catalog lookups: brands/models and states/cities."""

from __future__ import annotations

from typing import Any

from bama_mcp import http

_vehicle_cache: list[dict[str, Any]] | None = None
_region_cache: list[dict[str, Any]] | None = None


def reset_caches() -> None:
    global _vehicle_cache, _region_cache
    _vehicle_cache = None
    _region_cache = None


def vehicle_tree() -> list[dict[str, Any]]:
    global _vehicle_cache
    if _vehicle_cache is None:
        _vehicle_cache = http.get("/cad/api/filter/vehicle").json().get("data", []) or []
    return _vehicle_cache


def region_tree() -> list[dict[str, Any]]:
    global _region_cache
    if _region_cache is None:
        _region_cache = (
            http.get("/gen/api/filters/region", params={"vehicleCategory": "car"}).json().get("data", [])
            or []
        )
    return _region_cache


def brands() -> list[dict[str, str]]:
    out = []
    for brand in vehicle_tree():
        for item in brand.get("items", []):
            if item.get("type") == "brand" and item.get("select_all"):
                out.append({"title_fa": item.get("title"), "value": item.get("value")})
    return out


def models(brand: str) -> list[dict[str, str]]:
    for b in vehicle_tree():
        candidates: list = []
        if b.get("value") == brand:
            candidates = b.get("items", [])
        else:
            for item in b.get("items", []):
                if item.get("type") == "brand" and item.get("value") == brand:
                    candidates = b.get("items", [])
                    break
        if candidates:
            return [
                {"title_fa": sub.get("title"), "value": sub.get("value")}
                for sub in candidates
                if sub.get("type") == "model"
            ]
    return []


def cities() -> list[dict[str, str]]:
    out = []
    for state in region_tree():
        out.append({"title_fa": state.get("title"), "value": state.get("value"), "kind": "state"})
        for item in state.get("items", []):
            if item.get("type") == "city":
                out.append({"title_fa": item.get("title"), "value": item.get("value"), "kind": "city"})
    return out


def resolve_city(city: str) -> str | None:
    """Persian/English city name -> 'state,city' value. e.g. 'تهران' -> 'tehran,tehran'."""
    city = city.strip()
    if "," in city or "-" in city:
        return city.replace("-", ",")
    for state in region_tree():
        if city in (state.get("title"), state.get("value"), state.get("text")):
            return state.get("value")
        for item in state.get("items", []):
            if city in (item.get("title"), item.get("text"), item.get("value")):
                return item.get("value")
    return None

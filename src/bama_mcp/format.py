"""Pure helpers: price parsing, Persian formatting, ad shaping."""

from __future__ import annotations

import re
from typing import Any

BASE = "https://bama.ir"


def parse_price_toman(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


def fa_digits(s: str) -> str:
    return s.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def price_fa(toman: int | None, price_type: str | None = None) -> str:
    """410000000 -> '۴۱۰ میلیون تومان'. Handles billions, negotiable, zero."""
    if price_type == "negotiable" or not toman:
        return "توافقی"
    if toman >= 1_000_000_000:
        b = toman / 1_000_000_000
        num = f"{b:,.1f}" if b != int(b) else f"{int(b):,}"
        return f"{fa_digits(num)} میلیارد تومان"
    m = toman / 1_000_000
    num = f"{m:,.1f}" if m != int(m) else f"{int(m):,}"
    return f"{fa_digits(num)} میلیون تومان"


def ad_to_item(ad: dict[str, Any]) -> dict[str, Any]:
    d = ad.get("detail", {})
    p = ad.get("price", {})
    toman = parse_price_toman(p.get("price"))
    ptype = p.get("type")
    pfa = price_fa(toman, ptype)
    title = d.get("title") or ""
    subtitle = d.get("subtitle") or ""
    year = d.get("year") or ""
    mileage = d.get("mileage") or ""
    location = (d.get("location") or "").split("/")[0].strip()
    summary = f"{title} {subtitle}".strip()
    bits = [b for b in [year, pfa, mileage, location] if b and b != "-"]
    if bits:
        summary += " | " + "، ".join(bits)
    return {
        "code": d.get("code"),
        "title": d.get("title"),
        "subtitle": d.get("subtitle"),
        "summary_fa": summary,
        "brand": d.get("brand"),
        "brand_fa": d.get("brand_fa"),
        "year": d.get("year"),
        "mileage": d.get("mileage"),
        "location": d.get("location"),
        "time": d.get("time"),
        "body_status": d.get("body_status"),
        "transmission": d.get("transmission"),
        "fuel": d.get("fuel"),
        "color": d.get("color"),
        "price_type": ptype,
        "price_toman": toman,
        "price_fa": pfa,
        "dealer": (ad.get("dealer") or {}).get("name"),
        "seller_type": (ad.get("dealer") or {}).get("type"),
        "image": d.get("image"),
        "url": BASE + d.get("url", "") if d.get("url") else None,
    }


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out = []
    for it in items:
        key = it.get("code") or it.get("url")
        if not key:
            out.append(it)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def is_havaleh(item: dict[str, Any]) -> bool:
    return "حواله" in (item.get("title") or "")

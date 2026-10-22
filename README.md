[![bama-mcp: unofficial MCP server for bama.ir car ads](https://raw.githubusercontent.com/Amrzas/bama-mcp/main/.github/banner.jpg)](https://raw.githubusercontent.com/Amrzas/bama-mcp/main/.github/banner.jpg)

# bama-mcp: bama.ir MCP server for AI agents

**Let your AI agent search the Iranian car market (باما).**

An unofficial, read-only MCP server for [bama.ir](https://bama.ir), Iran's biggest car marketplace:
search ads by brand, model, city and price, read full ad details, compare prices in Toman, and browse
every brand, model and city — all from Claude, Cursor or Copilot.

[![PyPI](https://img.shields.io/pypi/v/bama-mcp?label=pypi&color=2563eb)](https://pypi.org/project/bama-mcp/)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab)](https://pypi.org/project/bama-mcp/)
[![CI](https://github.com/Amrzas/bama-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/Amrzas/bama-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/Amrzas/bama-mcp/blob/main/LICENSE)

---

## For AI agents

- **What:** unofficial MCP server for bama.ir (باما), the Iranian car marketplace. Persian and Finglish queries work; prices in Toman.
- **Install:** `claude mcp add bama -- uvx bama-mcp` (stdio, needs [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.10+). Snippets for Claude Desktop, Cursor, VS Code and Hermes below.
- **Auth:** none. No API key or account.
- **Access:** read-only. No login, no ads posted, nothing is bought or changed.
- **Tools:** 5: `search_cars`, `car_details`, `list_brands`, `list_models`, `list_cities`.
  Typical sequence: `list_brands` -> `list_models` -> `search_cars` -> `car_details`.
- **Use when:** the user wants Iranian car ads, prices, comparisons, or "is my car worth X" checks.
- **Do not use when:** the user wants to sell/post a car, needs their bama.ir account, or is outside Iran with a VPN on (bama.ir drops foreign IPs at TLS level).
- **Output:** compact JSON. Each item carries `summary_fa` (ready Persian one-liner for tables) and `price_fa` (`۴۱۰ میلیون تومان`). `price_toman` is an int or `null` (negotiable ads are never 0). Ad `code` and `url` pass between tools.

## Quick start

The server runs over stdio as `uvx bama-mcp`
(needs [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.10+; use the full path to `uvx`
from `which uvx` if your client cannot find it).

**Claude Code**

```
claude mcp add bama -- uvx bama-mcp
```

**Claude Desktop**

Settings → Developer → Edit Config, then add:

```json
{
  "mcpServers": {
    "bama": { "command": "uvx", "args": ["bama-mcp"] }
  }
}
```

**Cursor**

Add the same JSON block to `~/.cursor/mcp.json` (or `.cursor/mcp.json` inside a project), or click the button below:

[![Install in Cursor](https://raw.githubusercontent.com/Amrzas/bama-mcp/main/.github/cursor-install-dark.svg)](https://cursor.com/en/install-mcp?name=bama&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJiYW1hLW1jcCJdfQ%3D%3D)

In the terminal:

```
cursor --add-mcp bama -- uvx bama-mcp
```

**VS Code (Copilot agent mode)**

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "bama": { "type": "stdio", "command": "uvx", "args": ["bama-mcp"] }
  }
}
```

**Hermes**

```
hermes mcp add bama --command uvx --args bama-mcp
```

**Anything else**

It is a standard stdio MCP server: run `uvx bama-mcp`, or `pip install bama-mcp` and run `bama-mcp`.

Then just ask:

- "پژو ۲۰۶ زیر ۱.۵ میلیارد تو مشهد چی هست؟"
- "۵ تا ۲۰۶SD ارزون تو تهران: سال، قیمت"
- "جزئیات کامل این آگهی رو بده: https://bama.ir/car/detail-…"
- "سمند LX مدل ۱۴۰۰ تو اهواز چنده؟"
- "همه دنا پلاس رو با قیمت مرتب کن"

## What it can do

- 🔎 **Search** car ads by brand/model, city (all Iranian provinces and cities), price range and sort order
- 💸 **True prices in Persian**: `price_fa` (`۲۸۰ میلیون تومان`, `۴.۱ میلیارد تومان`, `توافقی`) plus `summary_fa` one-liners ready for tables
- 🧹 **Clean results**: duplicate ads removed, `حواله` (installment-slip) ads dropped by default, negotiable ads sink when sorting by price
- 🏙️ **Every city** in Iran, by Persian or English name
- 🔒 **Read-only by design**: no account, no posting, no contact — the agent finds, you decide

## Tools

| Tool | What it does |
|---|---|
| `search_cars` | Ads by `vehicle` (brand/model), `city`, `price_min`/`price_max` (Toman), `sort`, pagination. One call returns up to `limit` items (default 30) with `url` always included; `fields` (e.g. `title,price_fa,url` or `*`) controls the output size |
| `car_details` | One ad in full: price, year, colors, transmission, engine, seller description, photos |
| `list_brands` | Every brand with Farsi names (`پژو` -> `peugeot`) |
| `list_models` | Models of one brand (`peugeot` -> 206, 207, پارس, …) |
| `list_cities` | All provinces and cities, Farsi names |

## Good to know

- **Prices are in Toman.** `price_toman` is an integer; `price_fa` is the human-readable Persian form. A `negotiable` ad shows `توافقی`, never 0.
- **`حواله` ads are dropped by default** (`include_havaleh=false`): their price is a down-payment slip, not the car. Pass `include_havaleh=true` to keep them.
- **City names match Farsi or English** (`تهران`, `مشهد`, `tehran`). A province name returns the whole province (تهران includes ورامین and پاکدشت).
- **bama.ir blocks foreign IPs.** Run it from an Iranian IP with the VPN off; otherwise the TLS handshake is dropped and the tool answers a clear `bama_timeout` error. `BAMA_MCP_PROXY` sets an HTTP proxy that exits in Iran.
- **Every bama page holds 30 ads** — the API ignores smaller `pageSize` values, so one call returns up to 30 items and `page` moves in 30-ad steps.
- **Token-friendly by default.** One call returns at most `limit` items (default 30, cap 30 per call) with a compact field set (~12 fields incl. `summary_fa`, `price_fa`, `url`). Narrow it to `fields=title,price_fa,url`, widen to `fields=*`. Walk pages with `page = page + pages_fetched` whenever `truncated` is `true`. With `sort=4` (cheapest) plus `price_max` — or `sort=3` plus `price_min` — fetching stops as soon as the sorted list passes the bound, so bounded results are usually complete in one call.

## FAQ

**Is it official, safe and free?** It is unofficial, open source (MIT) and free. It is read-only, needs no account or API key, and runs on your machine with no hosted server in between.

**It times out / errors immediately.** bama.ir drops foreign IPs at the TLS level. Turn the VPN off, or set `BAMA_MCP_PROXY` to a proxy that exits in Iran.

**The model filter returns brand-level results.** Known limitation (v0.1): `vehicle=peugeot,207` currently behaves like `vehicle=peugeot` — bama expects a different value format. Brand search is exact. City and price filters work.

**`car_details` says pass the full URL.** Correct: pass the `url` field from `search_cars`, not the ad `code` alone.

**What are `summary_fa` and `price_fa` for?** Ready-made Persian strings so the agent can render a table or sentence without reformatting numbers.

## فارسی: سرور MCP باما

سرور **bama-mcp** یک ابزار غیررسمی و فقط‌خواندنی برای باما (bama.ir) است. به دستیار هوش مصنوعی شما (Claude، Cursor، Copilot و ...) اجازه می‌دهد آگهی‌های خودرو را بر اساس برند، مدل، شهر و قیمت جستجو کند، جزئیات کامل هر آگهی را بخواند و همه برندها و شهرهای ایران را ببیند.

- فقط خواندنی است: وارد حساب نمی‌شوید، آگهی ثبت نمی‌شود و هیچ چیزی خرید یا تغییر داده نمی‌شود.
- قیمت‌ها به تومان است و به صورت فارسی (`۲۸۰ میلیون تومان`) نمایش داده می‌شود.
- روی سیستم خود شما اجرا می‌شود و به هیچ سرور واسطی داده نمی‌فرستد.

**نصب در Claude Code:**

```
claude mcp add bama -- uvx bama-mcp
```

برای Claude Desktop، Cursor، VS Code و Hermes هم نمونه تنظیمات در بالای همین صفحه (بخش Quick start) آمده است.

بعد بپرسید: «پژو ۲۰۶ زیر ۱.۵ میلیارد تو مشهد چی هست؟»

**نکته:** سرور باید روی سیستمی با IP ایران و بدون VPN اجرا شود، چون باما درخواست‌های خارجی را در سطح TLS مسدود می‌کند.

## Development

```
git clone https://github.com/Amrzas/bama-mcp && cd bama-mcp
uv sync --group dev
uv run pytest                # offline, against recorded responses
uv run pytest -m live        # real bama.ir API (needs an Iranian IP)
uv run ruff check src tests
```

Tools live in `src/bama_mcp/` (`server.py`, pure helpers in `format.py`, catalog lookups in `catalog.py`, shared client in `http.py`).
Issues and PRs are welcome, especially new tools and fixes for API changes.

Releases: bump the version in `pyproject.toml` and `server.json`, then push a `v*` tag.
GitHub Actions tests, publishes to PyPI and creates the GitHub Release.

## Disclaimer

Unofficial; not affiliated with Bama. Read-only access to the data of public pages. Keep request rates low.
If this saves you clicks, a star helps others find it.

## License

[MIT](https://github.com/Amrzas/bama-mcp/blob/main/LICENSE)

#!/usr/bin/env python3
"""Fetch recent AGMARKNET mandi observations and import them into AgriCare.

The public API mirror documents that its records originate from the
Government of India's data.gov.in AGMARKNET dataset. It exposes only a rolling
30-day window; this script does not fabricate or backfill missing observations.
Prices are stored as INR/quintal.
"""
from __future__ import annotations
import argparse
import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.analytics import import_mandi_rows  # noqa: E402

API_URL = "https://api.dharun.dev/v1/mandi"
SOURCE = "AGMARKNET (data.gov.in), retrieved via api.dharun.dev"
FIELDS = ["state", "district", "market", "commodity", "variety", "grade",
          "arrival_date", "min_price", "max_price", "modal_price", "arrivals"]


def extract_rows(payload: Any) -> list[dict]:
    """Accept documented {data:[...]} response and common list wrappers."""
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("data") or payload.get("records") or payload.get("results") or []
        if isinstance(rows, dict):
            rows = rows.get("data") or rows.get("records") or []
    else:
        rows = []
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def normalize_row(row: dict) -> dict:
    """Map API field variants into the project's canonical import headings."""
    aliases = {
        "state": ("state", "state_name"),
        "district": ("district", "district_name"),
        "market": ("market", "mandi", "market_name", "market_center_name"),
        "commodity": ("commodity", "commodity_name", "crop"),
        "variety": ("variety",), "grade": ("grade",),
        "arrival_date": ("arrival_date", "date", "report_date"),
        "min_price": ("min_price", "minimum_price"),
        "max_price": ("max_price", "maximum_price"),
        "modal_price": ("modal_price", "modal"),
        "arrivals": ("arrivals", "arrival_quantity", "quantity"),
    }
    low = {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items()}
    out = {}
    for target, names in aliases.items():
        out[target] = next((low[n] for n in names if low.get(n) not in (None, "")), "")
    return out


def iso_date(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:10], fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(raw[:10]).date().isoformat()
    except ValueError:
        return raw[:10]


def fetch(state: str, days: int, limit: int, session=requests) -> list[dict]:
    """Fetch each date in the API's documented rolling 30-day availability."""
    if not 1 <= days <= 30:
        raise ValueError("--days must be between 1 and 30; the source API exposes a rolling 30-day window.")
    today = date.today()
    collected: dict[tuple, dict] = {}
    for offset in range(days):
        day = (today - timedelta(days=offset)).isoformat()
        response = session.get(API_URL, params={"state": state, "date": day, "limit": limit}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        for raw in extract_rows(payload):
            row = normalize_row(raw)
            if not row["arrival_date"]:
                row["arrival_date"] = day
            row["arrival_date"] = iso_date(row["arrival_date"])
            # Keep only source rows matching the requested state/date when supplied.
            if row["state"] and row["state"].strip().casefold() != state.casefold():
                continue
            if row["arrival_date"] != day:
                continue
            if not row["commodity"]:
                continue
            key = tuple(str(row.get(k, "")) for k in ("state", "district", "market", "commodity", "variety", "grade", "arrival_date"))
            collected[key] = row
    return list(collected.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch recent official-source AGMARKNET prices for AgriCare")
    parser.add_argument("--state", default="Telangana", help="State name; default: Telangana")
    parser.add_argument("--days", type=int, default=30, help="Recent days to request (1-30; default 30)")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum rows per source date (1-1000)")
    parser.add_argument("--output", default="data/agmarknet_recent.csv", help="CSV output path")
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    try:
        rows = fetch(args.state, args.days, args.limit)
    except (requests.RequestException, ValueError) as exc:
        raise SystemExit(f"AGMARKNET data could not be fetched: {exc}\nNo market records were inserted.")
    if not rows:
        raise SystemExit("The source returned no matching observations. No market records were inserted; try again later or another state.")
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    imported = import_mandi_rows(rows, f"{SOURCE}; retrieved {datetime.now().astimezone().isoformat(timespec='seconds')}", "daily")
    dates = sorted(str(r["arrival_date"])[:10] for r in rows)
    print("AGMARKNET import completed.")
    print(f"State: {args.state}")
    print(f"Rows fetched: {len(rows)} | imported/updated: {imported['imported_or_updated']} | skipped: {imported['skipped_invalid']}")
    print(f"Observed dates: {dates[0]} to {dates[-1]}")
    print("Price unit: INR per quintal (₹/qtl), as documented by the source API.")
    print(f"CSV saved: {output}")
    print("Source: Government of India AGMARKNET/data.gov.in, retrieved through api.dharun.dev; latest rolling 30-day data only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

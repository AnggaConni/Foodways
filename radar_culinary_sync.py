#!/usr/bin/env python3
"""Build Foodways AI culinary candidates from ICH-Radar data.json."""

from __future__ import annotations

import json
from pathlib import Path

SOURCE = Path("ich_radar_data.json")
OUTPUT = Path("ai_culinary.json")


def is_culinary(item: dict) -> bool:
    categories = item.get("categories") or []
    if not isinstance(categories, list):
        categories = [categories]
    category_text = " ".join(str(x) for x in categories + [item.get("category", "")]).lower()

    analysis = item.get("resume_analisa") or {}
    tags = analysis.get("gemini_tags") or []
    text = " ".join(
        [
            str(item.get("element_name", "")),
            str(analysis.get("description", "")),
            str(analysis.get("cultural_significance", "")),
            *(str(x) for x in tags),
        ]
    ).lower()

    explicit = "culinary" in category_text or "culinary traditions" in category_text
    lexical = any(
        token in text
        for token in (
            "food", "cuisine", "culinary", "cooking", "recipe", "gastronomy",
            "dish", "meal", "foodways", "bread", "rice", "noodle", "sauce",
            "spice", "fish", "tea", "coffee", "ferment", "beverage", "drink",
        )
    )
    return explicit or lexical


def normalize(item: dict) -> dict:
    loc = item.get("location") or {}
    analysis = item.get("resume_analisa") or {}
    categories = item.get("categories") or []
    if not isinstance(categories, list):
        categories = [categories]

    return {
        "source_id": item.get("id"),
        "element_name": item.get("element_name", ""),
        "category": " | ".join(str(x) for x in categories) or item.get("category", ""),
        "country": loc.get("country", ""),
        "provinces": loc.get("provinces") if isinstance(loc.get("provinces"), list) else [],
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "thumbnail_url": item.get("thumbnail_url", ""),
        "description": analysis.get("description", ""),
        "cultural_significance": analysis.get("cultural_significance", ""),
        "tags": analysis.get("gemini_tags") if isinstance(analysis.get("gemini_tags"), list) else [],
        "completion_status": item.get("completion_status", ""),
        "shared_heritage": item.get("shared_heritage_detection") or {},
        "source_urls": item.get("source_urls") if isinstance(item.get("source_urls"), list) else [],
        "scraped_at": item.get("scraped_at"),
    }


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    inventory = payload.get("inventory", []) if isinstance(payload, dict) else payload
    records = [normalize(item) for item in inventory if isinstance(item, dict) and is_culinary(item)]

    records.sort(key=lambda x: (x.get("country", ""), x.get("element_name", "").lower()))

    OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} culinary records to {OUTPUT}")


if __name__ == "__main__":
    main()

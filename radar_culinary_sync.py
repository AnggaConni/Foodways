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
    category_text = " | ".join(str(x) for x in categories + [item.get("category", "")])
    return any("culinary traditions" in str(x).lower() for x in categories + [item.get("category", "")])


def format_value(value):
    if value is None or value == "" or value == [] or value == {}:
        return ""
    if isinstance(value, list):
        return "\n• ".join(str(v) for v in value if v not in (None, ""))
    if isinstance(value, dict):
        parts = []
        for key, val in value.items():
            text = format_value(val)
            if text:
                parts.append(f"{key}: {text}")
        return "\n".join(parts)
    return str(value)


def stacked_description(item: dict) -> str:
    sections = []

    def add(title, value):
        text = format_value(value).strip()
        if text:
            sections.append(f"## {title}\n{text}")

    analysis = item.get("resume_analisa") or {}
    process = item.get("resume_tata_cara") or {}

    add("Description", analysis.get("description"))
    add("Cultural Significance", analysis.get("cultural_significance"))
    add("Tools, Materials & Ingredients", process.get("materials_and_tools"))
    add("Step-by-Step Process", process.get("step_by_step"))
    add("Process Type", process.get("type"))
    add("AI Tags", analysis.get("gemini_tags") or item.get("gemini_tags"))
    add("Shared Heritage Detection", item.get("shared_heritage_detection"))
    add("Categories", item.get("categories") or item.get("category"))
    add("Location", item.get("location"))
    add("Completion Status", item.get("completion_status"))
    add("DRR Relevance", item.get("drr_relevance"))
    add("DRR Category", item.get("drr_category"))
    add("Hazard Categories", item.get("hazard_categories"))
    add("Resource & Opportunity", item.get("resource_opportunity"))

    return "\n\n".join(sections)


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
        "description": stacked_description(item),
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
    records = [normalize(item) for item in inventory if isinstance(item, dict) and is_culinary(item)
                and isinstance((item.get("location") or {}).get("lat"), (int, float))
                and isinstance((item.get("location") or {}).get("lng"), (int, float))]

    records.sort(key=lambda x: (x.get("country", ""), x.get("element_name", "").lower()))

    OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} culinary records to {OUTPUT}")


if __name__ == "__main__":
    main()

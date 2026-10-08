#!/usr/bin/env python3
"""
Foodways Historical Research Pipeline

Pipeline:
  1. Read AI-discovered culinary signals from ai_culinary.json.
  2. Optionally read the human-curated Foodways records from Supabase.
  3. Ask TinyFish Search for live web evidence about historical dates,
     origins, dissemination and possible trade corridors.
  4. Ask Gemini to inspect the TinyFish evidence + human/AI records and
     return a structured heuristic assessment.
  5. Persist results to foodways_timeline_research.json and cache individual
     research results so unchanged records are not re-researched.

Important:
  - This produces a RESEARCH / HEURISTIC DATASET only.
  - It does NOT write anything to Supabase.
  - Human curation remains the final authority for Foodways.
  - Human cross-check is intentionally DISABLED by default for the first research pass.
  - API keys are read only from environment variables / GitHub Secrets.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
AI_DATA = ROOT / "ai_culinary.json"
CACHE_FILE = ROOT / "foodways_timeline_cache.json"
OUTPUT_FILE = ROOT / "foodways_timeline_research.json"

TINYFISH_SEARCH_URL = os.getenv(
    "TINYFISH_SEARCH_URL", "https://api.search.tinyfish.ai"
)
SUPABASE_URL = os.getenv(
    "SUPABASE_URL", "https://yyjwodgywizjbnrvdnpn.supabase.co"
)
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
ENABLE_HUMAN_CROSSCHECK = os.getenv("ENABLE_HUMAN_CROSSCHECK", "0") == "1"

TINYFISH_KEY = os.getenv("TINYFISH_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-3.8-flash").strip()

MAX_RECORDS = int(os.getenv("TIMELINE_MAX_RECORDS", "0"))  # 0 = all
SEARCH_RESULTS = int(os.getenv("TINYFISH_RESULTS", "8"))
REQUEST_DELAY = float(os.getenv("TINYFISH_DELAY_SECONDS", "0.8"))
FORCE_RESEARCH = os.getenv("FORCE_TIMELINE_RESEARCH", "0") == "1"


class DateEvidence(BaseModel):
    year: int = Field(description="A four-digit year explicitly supported by a source.")
    claim: str = Field(description="What the source says about the year.")
    source_url: str = Field(description="Exact source URL supporting the claim.")
    confidence: float = Field(ge=0, le=1, description="Confidence that the source supports the date.")


class RouteHypothesis(BaseModel):
    route: str = Field(description="Named trade route, exchange network, corridor or maritime network.")
    relationship: str = Field(description="How the foodway may relate to this route.")
    evidence: list[str] = Field(default_factory=list, description="Evidence statements grounded in the supplied web results.")
    confidence: float = Field(ge=0, le=1, description="Heuristic confidence, not historical proof.")


class TimelineAssessment(BaseModel):
    probable_origin_country: str | None = None
    probable_origin_place: str | None = None
    earliest_supported_year: int | None = None
    date_evidence: list[DateEvidence] = Field(default_factory=list)
    route_hypotheses: list[RouteHypothesis] = Field(default_factory=list)
    date_confidence: float = Field(ge=0, le=1, description="Confidence in the earliest supported year.")
    origin_confidence: float = Field(ge=0, le=1, description="Confidence in the probable origin.")
    trade_route_confidence: float = Field(ge=0, le=1, description="Confidence in the overall trade-route interpretation.")
    origin_reasoning: str = ""
    uncertainty: str = ""
    contradictions: list[str] = Field(default_factory=list)


def fail(message: str) -> None:
    print(f"[timeline] ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 45,
) -> Any:
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}{'&' if '?' in url else '?'}{query}"

    body = None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "Foodways-Timeline-Research/1.0",
    }
    if headers:
        request_headers.update(headers)

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, headers=request_headers, method=method, data=body)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"HTTP {response.status}: {raw[:500]}")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail[:700]}") from exc


def normalize_text(value: str | None) -> str:
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def record_signature(record: dict[str, Any], human: dict[str, Any] | None) -> str:
    material = {
        "ai": record,
        "human": human or {},
    }
    canonical = json.dumps(material, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_human_records() -> list[dict[str, Any]]:
    if not SUPABASE_KEY:
        return []

    url = f'{SUPABASE_URL.rstrip("/")}/rest/v1/{urllib.parse.quote("Heritage Foodways")}'
    data = request_json(
        url,
        params={"select": "*", "order": "id"},
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
    )
    return data if isinstance(data, list) else []


def build_human_index(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (
            normalize_text(record.get("food_name")),
            normalize_text(record.get("country")),
        )
        if key[0]:
            index[key] = record
    return index


def tinyfish_search(query: str) -> list[dict[str, Any]]:
    data = request_json(
        TINYFISH_SEARCH_URL,
        params={"query": query},
        headers={"X-API-Key": TINYFISH_KEY},
    )

    raw_results = data.get("results", []) if isinstance(data, dict) else []
    results: list[dict[str, Any]] = []
    for item in raw_results[:SEARCH_RESULTS]:
        results.append(
            {
                "position": item.get("position"),
                "site_name": item.get("site_name"),
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "url": item.get("url"),
            }
        )
    return results


def evidence_prompt(
    ai_record: dict[str, Any],
    human_record: dict[str, Any] | None,
    web_results: list[dict[str, Any]],
) -> str:
    return f"""
You are the historical research assistant for the Foodways shared-heritage project.

Your job is NOT to invent history. Inspect the supplied AI-discovered record, the
human-curated Foodways record (when available), and live web-search results from
TinyFish. Produce a cautious, evidence-grounded heuristic assessment.

AI-DISCOVERED RECORD:
{json.dumps(ai_record, ensure_ascii=False, indent=2)}

HUMAN-CURATED FOODWAYS RECORD:
{json.dumps(human_record or {}, ensure_ascii=False, indent=2)}

TINYFISH WEB RESULTS:
{json.dumps(web_results, ensure_ascii=False, indent=2)}

Tasks:
1. Find the earliest explicitly supported YEAR in the supplied web evidence that
   is materially about this food/tradition, its documented practice, or a directly
   relevant historical record. Do NOT infer a year merely from the current page date.
2. Identify the most defensible probable origin country/place, but return null if
   the evidence is insufficient or contradictory.
3. Identify possible trade routes, maritime networks, migration corridors, colonial
   exchanges or other dissemination pathways. These are HYPOTHESES, not facts.
4. Prefer primary/official/academic sources when the supplied results contain them.
5. Cite exact URLs from the supplied TinyFish results only. Do not invent URLs.
6. Explicitly describe contradictions or uncertainty.
7. Human-curated Foodways data is a reference layer, NOT proof that the timeline
   or route hypothesis is correct.
8. Do not treat a UNESCO inscription year as the origin year unless the source
   explicitly supports that interpretation.
9. Score date_confidence, origin_confidence and trade_route_confidence independently.
   Use 0.90-1.00 only when multiple strong sources agree; 0.70-0.89 when there is
   strong but incomplete evidence; 0.40-0.69 when evidence is mixed/indirect; and
   below 0.40 when the hypothesis is weak. Do not inflate scores merely because
   a claim sounds plausible.

Return strict JSON matching the requested schema.
""".strip()


def gemini_inspect(
    client: genai.Client,
    ai_record: dict[str, Any],
    human_record: dict[str, Any] | None,
    web_results: list[dict[str, Any]],
) -> TimelineAssessment:
    prompt = evidence_prompt(ai_record, human_record, web_results)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": TimelineAssessment,
        },
    )

    if getattr(response, "parsed", None) is not None:
        parsed = response.parsed
        if isinstance(parsed, TimelineAssessment):
            return parsed
        return TimelineAssessment.model_validate(parsed)

    text = getattr(response, "text", "") or ""
    return TimelineAssessment.model_validate_json(text)


def main() -> None:
    if not TINYFISH_KEY:
        fail("TINYFISH_API_KEY is required.")
    if not GEMINI_KEY:
        fail("GEMINI_API_KEY is required.")

    os.environ["GEMINI_API_KEY"] = GEMINI_KEY
    client = genai.Client(api_key=GEMINI_KEY)

    ai_payload = load_json(AI_DATA, [])
    if isinstance(ai_payload, dict):
        records = ai_payload.get("records", [])
    else:
        records = ai_payload

    if not isinstance(records, list):
        fail("ai_culinary.json does not contain a list of records.")

    if ENABLE_HUMAN_CROSSCHECK:
        human_records = load_human_records()
        human_index = build_human_index(human_records)
    else:
        human_records = []
        human_index = {}
        print("[timeline] Human cross-check disabled for this research pass.")
    cache = load_json(CACHE_FILE, {})

    candidates = []
    for record in records:
        key = (
            normalize_text(record.get("element_name")),
            normalize_text(record.get("country")),
        )
        human = human_index.get(key)
        candidates.append((record, human))

    if MAX_RECORDS > 0:
        candidates = candidates[:MAX_RECORDS]

    results = []
    stats = {"ai_records": len(records), "human_records": len(human_records), "researched": 0, "cached": 0, "errors": 0}

    for index, (record, human) in enumerate(candidates, start=1):
        source_id = record.get("source_id") or f"food-{index}"
        signature = record_signature(record, human)
        cached = cache.get(source_id)

        if cached and cached.get("signature") == signature and not FORCE_RESEARCH:
            results.append(cached["result"])
            stats["cached"] += 1
            print(f"[timeline] {index}/{len(candidates)} CACHE {source_id} {record.get('element_name')}")
            continue

        food_name = record.get("element_name", "")
        country = record.get("country", "")
        description = str(record.get("description", ""))[:2500]
        human_origin = {
            "origin_food_name": human.get("origin_food_name") if human else None,
            "origin_country": human.get("origin_country") if human else None,
            "origin_lat": human.get("origin_lat") if human else None,
            "origin_lng": human.get("origin_lng") if human else None,
            "research_links": human.get("research_links") if human else None,
        }

        query = (
            f'"{food_name}" history origin earliest documented trade route '
            f'{country} culinary tradition {description[:500]}'
        )

        try:
            web_results = tinyfish_search(query)
            assessment = gemini_inspect(client, record, human, web_results)

            date_conf = float(assessment.date_confidence)
            origin_conf = float(assessment.origin_confidence)
            trade_conf = float(assessment.trade_route_confidence)
            overall_conf = round(
                (0.40 * date_conf) + (0.30 * origin_conf) + (0.30 * trade_conf),
                4,
            )

            date_conf = float(assessment.date_confidence)
            origin_conf = float(assessment.origin_confidence)
            trade_conf = float(assessment.trade_route_confidence)
            overall_conf = round(
                (0.40 * date_conf) + (0.30 * origin_conf) + (0.30 * trade_conf),
                4,
            )

            result = {
                "source_id": source_id,
                "food_name": food_name,
                "ai_country": country,
                "ai_location": {
                    "lat": record.get("lat"),
                    "lng": record.get("lng"),
                    "provinces": record.get("provinces", []),
                },
                "human_match": human is not None,
                "human_record_id": human.get("id") if human else None,
                "human_origin": human_origin,
                "assessment": assessment.model_dump(),
                "confidence": {
                    "date": round(date_conf, 4),
                    "origin": round(origin_conf, 4),
                    "trade_route": round(trade_conf, 4),
                    "overall": overall_conf,
                    "band": (
                        "High" if overall_conf >= 0.80 else
                        "Medium" if overall_conf >= 0.60 else
                        "Low" if overall_conf >= 0.40 else
                        "Very Low"
                    ),
                },
                "tinyfish_sources": web_results,
                "heuristic_disclaimer": (
                    "Research-assistant output only. Timeline dates, probable origins "
                    "and trade-route relationships are heuristic hypotheses generated "
                    "from AI-discovered data and live web evidence. They have not yet "
                    "been verified by a human curator."
                ),
                "researched_at": datetime.now(timezone.utc).isoformat(),
            }

            cache[source_id] = {"signature": signature, "result": result}
            results.append(result)
            stats["researched"] += 1
            print(f"[timeline] {index}/{len(candidates)} OK {source_id} {food_name}")

        except Exception as exc:
            stats["errors"] += 1
            print(f"[timeline] {index}/{len(candidates)} ERROR {source_id}: {exc}", file=sys.stderr)

        time.sleep(max(0, REQUEST_DELAY))

    OUTPUT_FILE.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "stats": stats,
                "disclaimer": (
                    "Heuristic research dataset. AI is currently an assistant for "
                    "discovery and hypothesis generation. No human curator has yet "
                    "verified the complete timeline or causal trade-route relationships."
                ),
                "records": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        "[timeline] DONE "
        f"researched={stats['researched']} cached={stats['cached']} errors={stats['errors']}"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Foodways Supabase keep-alive.

Makes a tiny read-only Supabase REST request so the Free-plan project
continues to receive database activity.

No third-party Python packages are required.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TABLE = "Heritage Foodways"


def load_supabase_config() -> tuple[str, str]:
    """
    Prefer GitHub Actions environment variables, but fall back to the
    publishable browser configuration already present in index.html.
    The publishable key is intentionally client-side/public in Supabase.
    """
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()

    if url and key:
        return url.rstrip("/"), key

    html = Path("index.html").read_text(encoding="utf-8")
    url_match = re.search(r"const\s+SUPABASE_URL\s*=\s*['\"]([^'\"]+)['\"]", html)
    key_match = re.search(
        r"const\s+SUPABASE_PUBLISHABLE_KEY\s*=\s*['\"]([^'\"]+)['\"]", html
    )

    if not url_match or not key_match:
        raise RuntimeError("Could not find Supabase public configuration.")

    return url_match.group(1).rstrip("/"), key_match.group(1)


def main() -> int:
    supabase_url, supabase_key = load_supabase_config()
    query = urllib.parse.urlencode({"select": "id", "limit": "1"})
    url = f"{supabase_url}/rest/v1/{urllib.parse.quote(TABLE)}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Accept": "application/json",
            "User-Agent": "Foodways-Supabase-KeepAlive/1.0",
        },
        method="GET",
    )

    started = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            if response.status != 200:
                raise RuntimeError(f"Unexpected HTTP {response.status}: {body[:300]}")

            payload = json.loads(body)
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "timestamp_utc": started,
                        "http_status": response.status,
                        "rows_returned": len(payload) if isinstance(payload, list) else 0,
                    }
                )
            )
            return 0

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "status": "error",
                    "timestamp_utc": started,
                    "http_status": exc.code,
                    "detail": detail[:500],
                }
            ),
            file=sys.stderr,
        )
        return 1

    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "timestamp_utc": started,
                    "detail": str(exc)[:500],
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

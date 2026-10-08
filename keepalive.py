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
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://yyjwodgywizjbnrvdnpn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_3dTLdT8jsmdLzG_fbM5OxQ_Yt9lE9Pg")
TABLE = 'Heritage Foodways'


def main() -> int:
    query = urllib.parse.urlencode({"select": "id", "limit": "1"})
    url = f"{SUPABASE_URL}/rest/v1/{urllib.parse.quote(TABLE)}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
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

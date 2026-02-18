"""Lightweight Discord notifier for operational alerts."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict


def send_discord_alert(webhook_url: str, title: str, description: str, details: Dict | None = None) -> Dict:
    if not webhook_url:
        return {"ok": False, "message": "Missing Discord webhook URL."}

    content = f"**{title}**\n{description}"
    if details:
        content += "\n```json\n" + json.dumps(details, indent=2) + "\n```"

    payload = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status not in (200, 204):
                return {"ok": False, "message": f"Discord webhook failed with HTTP {response.status}"}
    except urllib.error.URLError as exc:
        return {"ok": False, "message": f"Discord webhook request failed: {exc.reason}"}
    except TimeoutError:
        return {"ok": False, "message": "Discord webhook request failed: timeout"}

    return {"ok": True, "message": "Discord alert sent."}

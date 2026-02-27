# app/menu_service.py

import os
import time
from typing import Dict, Any, Optional

import requests

from .logging_loki import loki


MENU_SERVICE_URL = os.getenv("MENU_SERVICE_URL")


def get_menu(user_id: str, channel: str, session_id: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch the restaurant menu from an external service (n8n webhook).

    NORMALIZATION RULES (PRESERVED FROM OLD SCRIPT):

    Raw n8n shape:
      [
        {
          "output": { "text": "Pepperoni - Pizza - 100\n..." }
        }
      ]

    Normalized:
      {
        "output": "Pepperoni - Pizza - 100\n..."
      }

    Also supports:
      {
         "output": "Some string"
      }
    """

    # Missing configuration
    if not MENU_SERVICE_URL:
        loki.log(
            "warning",
            {
                "event_type": "service_missing_config",
                "detail": "MENU_SERVICE_URL not set",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
            },
            service_type="menu_service",
            sync_mode="async",
            io="none",
            trace_id=trace_id,
        )
        return {}

    start = time.perf_counter()

    # ---- OUTGOING CALL LOG (async OUT) ----
    loki.log(
        "info",
        {
            "event_type": "service_call",
            "reason": "get_menu",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
        },
        service_type="menu_service",
        sync_mode="async",
        io="out",
        trace_id=trace_id,
    )

    try:
        resp = requests.get(MENU_SERVICE_URL, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        # ---------------------------------------------------
        # NORMALIZATION STEP (IDENTICAL TO OLD VERSION)
        # ---------------------------------------------------

        # If list, take first element
        if isinstance(data, list) and data:
            first = data[0]
        else:
            first = data

        # Expect dict with "output"
        if isinstance(first, dict):
            out = first.get("output")
        else:
            out = None

        # Flatten { "text": "..." }
        if isinstance(out, dict) and isinstance(out.get("text"), str):
            normalized = {"output": out["text"]}

        # Already string
        elif isinstance(out, str):
            normalized = {"output": out}

        # Unknown shape
        else:
            normalized = {}

        latency_ms = round((time.perf_counter() - start) * 1000.0, 3)

        # ---- INCOMING RESPONSE LOG (async IN) ----
        loki.log(
            "info",
            {
                "event_type": "service_return",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "latency_ms": latency_ms,
                "raw_shape": type(data).__name__,
            },
            service_type="menu_service",
            sync_mode="async",
            io="in",
            trace_id=trace_id,
        )

        return normalized

    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000.0, 3)

        # ---- ERROR LOG ----
        loki.log(
            "error",
            {
                "event_type": "service_error",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "latency_ms": latency_ms,
                "error": str(e),
            },
            service_type="menu_service",
            sync_mode="async",
            io="none",
            trace_id=trace_id,
        )

        return {}

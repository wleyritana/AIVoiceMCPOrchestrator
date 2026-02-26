import os
import time
from typing import Dict, Any, Optional

import requests

from app.observability.logging_loki import loki
from app.models.service_models import MenuResponse


MENU_SERVICE_URL = os.getenv("MENU_SERVICE_URL")


def fetch_menu(
    user_id: str,
    channel: str,
    session_id: str,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not MENU_SERVICE_URL:
        loki.log(
            "error",
            {
                "event_type": "service_missing_config",
                "detail": "MENU_SERVICE_URL not set",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "trace_id": trace_id,
            },
            service_type="menu_service",
            sync_mode="async",
            io="none",
        )
        return {}

    start = time.perf_counter()

    loki.log(
        "info",
        {
            "event_type": "service_call",
            "reason": "get_menu",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "trace_id": trace_id,
        },
        service_type="menu_service",
        sync_mode="async",
        io="out",
    )

    try:
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "channel": channel,
            "session_id": session_id,
        }
        if trace_id:
            payload["trace_id"] = trace_id

        resp = requests.post(MENU_SERVICE_URL, json=payload, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list) and data:
            first = data[0]
        else:
            first = data

        if isinstance(first, dict):
            candidate = first
        else:
            candidate = {}

        out = candidate.get("output")
        if isinstance(out, dict) and isinstance(out.get("text"), str):
            candidate = {**candidate, "output": out["text"]}

        try:
            menu = MenuResponse.parse_obj(candidate)
        except Exception as ve:
            latency_ms = round((time.perf_counter() - start) * 1000.0, 3)
            loki.log(
                "error",
                {
                    "event_type": "service_error",
                    "user": user_id,
                    "channel": channel,
                    "session_id": session_id,
                    "latency_ms": latency_ms,
                    "error": f"MenuResponse validation failed: {ve}",
                    "trace_id": trace_id,
                },
                service_type="menu_service",
                sync_mode="async",
                io="none",
            )
            return {}

        latency_ms = round((time.perf_counter() - start) * 1000.0, 3)

        loki.log(
            "info",
            {
                "event_type": "service_return",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "latency_ms": latency_ms,
                "raw_shape": type(data).__name__,
                "trace_id": trace_id,
            },
            service_type="menu_service",
            sync_mode="async",
            io="in",
        )

        return menu.dict(exclude_none=True)

    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000.0, 3)
        loki.log(
            "error",
            {
                "event_type": "service_error",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "latency_ms": latency_ms,
                "error": str(e),
                "trace_id": trace_id,
            },
            service_type="menu_service",
            sync_mode="async",
            io="none",
        )
        return {}

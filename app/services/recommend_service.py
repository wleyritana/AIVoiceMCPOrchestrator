import os
import time
from typing import Dict, Any, Optional

import requests

from app.observability.logging_loki import loki
from app.models.service_models import RecommendResponse


RECOMMEND_SERVICE_URL = os.getenv("RECOMMEND_SERVICE_URL")


def get_recommendations(
    user_id: str,
    channel: str,
    session_id: str,
    context: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not RECOMMEND_SERVICE_URL:
        loki.log(
            "error",
            {
                "event_type": "service_missing_config",
                "detail": "RECOMMEND_SERVICE_URL not set",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "trace_id": trace_id,
            },
            service_type="recommend_service",
            sync_mode="async",
            io="none",
        )
        return {}

    start = time.perf_counter()

    loki.log(
        "info",
        {
            "event_type": "service_call",
            "reason": "get_recommendations",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "trace_id": trace_id,
        },
        service_type="recommend_service",
        sync_mode="async",
        io="out",
    )

    try:
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "channel": channel,
            "session_id": session_id,
        }
        if context is not None:
            payload["context"] = context
        if trace_id:
            payload["trace_id"] = trace_id

        resp = requests.post(RECOMMEND_SERVICE_URL, json=payload, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, dict):
            if isinstance(data, list) and data:
                candidate = data[0]
            else:
                candidate = {}
        else:
            candidate = data

        try:
            rec = RecommendResponse.parse_obj(candidate)
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
                    "error": f"RecommendResponse validation failed: {ve}",
                    "trace_id": trace_id,
                },
                service_type="recommend_service",
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
            service_type="recommend_service",
            sync_mode="async",
            io="in",
        )

        return rec.dict(exclude_none=True)

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
            service_type="recommend_service",
            sync_mode="async",
            io="none",
        )
        return {}

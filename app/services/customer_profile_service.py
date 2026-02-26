import os
import time
from typing import Dict, Any, Optional

import requests

from app.observability.logging_loki import loki
from app.models.service_models import UserProfileResponse, SavePreferencesResponse


PROFILE_SERVICE_URL = os.getenv("PROFILE_SERVICE_URL")


def get_user_profile(
    user_id: str,
    channel: str,
    session_id: str,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not PROFILE_SERVICE_URL:
        loki.log(
            "error",
            {
                "event_type": "service_missing_config",
                "detail": "PROFILE_SERVICE_URL not set",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "trace_id": trace_id,
            },
            service_type="customer_profile_service",
            sync_mode="async",
            io="none",
        )
        return {}

    start = time.perf_counter()

    loki.log(
        "info",
        {
            "event_type": "service_call",
            "reason": "get_profile",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "trace_id": trace_id,
        },
        service_type="customer_profile_service",
        sync_mode="async",
        io="out",
    )

    try:
        payload: Dict[str, Any] = {
            "mode": "get_profile",
            "user_id": user_id,
            "channel": channel,
            "session_id": session_id,
        }
        if trace_id:
            payload["trace_id"] = trace_id

        resp = requests.post(PROFILE_SERVICE_URL, json=payload, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list) and data:
            candidate = data[0]
        elif isinstance(data, dict):
            candidate = data
        else:
            candidate = {}

        try:
            prof = UserProfileResponse.parse_obj(candidate)
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
                    "error": f"UserProfileResponse validation failed: {ve}",
                    "trace_id": trace_id,
                },
                service_type="customer_profile_service",
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
            service_type="customer_profile_service",
            sync_mode="async",
            io="in",
        )

        return prof.dict(exclude_none=True)

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
            service_type="customer_profile_service",
            sync_mode="async",
            io="none",
        )
        return {}


def save_user_preferences(
    user_id: str,
    channel: str,
    session_id: str,
    preferences: Dict[str, Any],
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not PROFILE_SERVICE_URL:
        loki.log(
            "error",
            {
                "event_type": "service_missing_config",
                "detail": "PROFILE_SERVICE_URL not set",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "trace_id": trace_id,
            },
            service_type="customer_profile_service",
            sync_mode="async",
            io="none",
        )
        return {}

    start = time.perf_counter()

    loki.log(
        "info",
        {
            "event_type": "service_call",
            "reason": "save_preferences",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "trace_id": trace_id,
        },
        service_type="customer_profile_service",
        sync_mode="async",
        io="out",
    )

    try:
        payload: Dict[str, Any] = {
            "mode": "save_preferences",
            "user_id": user_id,
            "channel": channel,
            "session_id": session_id,
            "preferences": preferences,
        }
        if trace_id:
            payload["trace_id"] = trace_id

        resp = requests.post(PROFILE_SERVICE_URL, json=payload, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list) and data:
            candidate = data[0]
        elif isinstance(data, dict):
            candidate = data
        else:
            candidate = {}

        try:
            ack = SavePreferencesResponse.parse_obj(candidate)
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
                    "error": f"SavePreferencesResponse validation failed: {ve}",
                    "trace_id": trace_id,
                },
                service_type="customer_profile_service",
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
            service_type="customer_profile_service",
            sync_mode="async",
            io="in",
        )

        return ack.dict(exclude_none=True)

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
            service_type="customer_profile_service",
            sync_mode="async",
            io="none",
        )
        return {}

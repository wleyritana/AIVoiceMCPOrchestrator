import os
import time
from typing import Dict, Any, List, Optional

import requests

from app.observability.logging_loki import loki
from app.models.service_models import OrderItem, OrderResponse


ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL")


def place_order(
    user_id: str,
    channel: str,
    session_id: str,
    items: List[Dict[str, Any]],
    payment_method: str,
    delivery_mode: str,
    special_instructions: Optional[str] = None,
    table_number: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not ORDER_SERVICE_URL:
        loki.log(
            "error",
            {
                "event_type": "service_missing_config",
                "detail": "ORDER_SERVICE_URL not set",
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "trace_id": trace_id,
            },
            service_type="order_service",
            sync_mode="async",
            io="none",
        )
        return {}

    start = time.perf_counter()

    loki.log(
        "info",
        {
            "event_type": "service_call",
            "reason": "place_order",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "trace_id": trace_id,
        },
        service_type="order_service",
        sync_mode="async",
        io="out",
    )

    try:
        order_items = [OrderItem.parse_obj(i).dict(exclude_none=True) for i in items]

        payload: Dict[str, Any] = {
            "user_id": user_id,
            "channel": channel,
            "session_id": session_id,
            "items": order_items,
            "payment_method": payment_method,
            "delivery_mode": delivery_mode,
        }
        if special_instructions is not None:
            payload["special_instructions"] = special_instructions
        if table_number is not None:
            payload["table_number"] = table_number
        if trace_id:
            payload["trace_id"] = trace_id

        resp = requests.post(ORDER_SERVICE_URL, json=payload, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list) and data:
            first = data[0]
        else:
            first = data

        if not isinstance(first, dict):
            first = {}

        try:
            order = OrderResponse.parse_obj(first)
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
                    "error": f"OrderResponse validation failed: {ve}",
                    "trace_id": trace_id,
                },
                service_type="order_service",
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
            service_type="order_service",
            sync_mode="async",
            io="in",
        )

        return order.dict(exclude_none=True)

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
            service_type="order_service",
            sync_mode="async",
            io="none",
        )
        return {}

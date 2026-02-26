from __future__ import annotations

import time
from typing import Optional, List, Dict, Any

from pydantic import BaseModel

from app.observability.logging_loki import loki
from app.tools.base_tool import ToolCallContext
from app.tools.registry import get_tool_registry


class FlowServiceResult(BaseModel):
    reply_text: str
    route: str


def run_flow(
    intent: str,
    text: str,
    user_id: str,
    channel: str,
    session_id: str,
    trace_id: Optional[str] = None,
    order_items: Optional[List[Dict[str, Any]]] = None,
    order_payment_method: Optional[str] = None,
    order_delivery_mode: Optional[str] = None,
    order_special_instructions: Optional[str] = None,
    order_table_number: Optional[str] = None,
    tracking_order_id: Optional[str] = None,
) -> FlowServiceResult:

    loki.log(
        "info",
        {
            "event_type": "flow_start",
            "intent": intent,
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "trace_id": trace_id,
        },
        service_type="flow_service",
        sync_mode="sync",
        io="in",
    )

    registry = get_tool_registry()
    ctx = ToolCallContext(
        user_id=user_id,
        channel=channel,
        session_id=session_id,
        trace_id=trace_id,
    )

    if intent == "menu":
        start = time.perf_counter()

        loki.log(
            "info",
            {
                "event_type": "flow_menu_call",
                "intent": intent,
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "message": "calling menu tool",
                "trace_id": trace_id,
            },
            service_type="flow_service",
            sync_mode="async",
            io="out",
        )

        menu_tool = registry.get("menu")
        tool_result = menu_tool.call(ctx)

        latency_ms = round((time.perf_counter() - start) * 1000.0, 3)

        loki.log(
            "info",
            {
                "event_type": "flow_menu_return",
                "intent": intent,
                "latency_ms": latency_ms,
                "user": user_id,
                "channel": channel,
                "session_id": session_id,
                "payload_received": bool(tool_result.data),
                "trace_id": trace_id,
            },
            service_type="flow_service",
            sync_mode="async",
            io="in",
        )

        reply_text = tool_result.raw_text or (
            "I tried to fetch the menu but didn't receive any usable data. "
            "Please try again in a moment."
        )

        return FlowServiceResult(reply_text=reply_text, route="menu")

    if intent == "order":
        if not order_items:
            reply_text = (
                "I can place your order, but I don't yet know which items you want.\n\n"
                "Please either:\n"
                "- Tell me which dishes (for example: '1 Garlic Chicken and 2 Sisig'), or\n"
                "- Use a UI that sends the selected items as structured data to this MCP.\n\n"
                "Once I have your selected items, I can send them to the ordering service."
            )
            return FlowServiceResult(reply_text=reply_text, route="order_missing_items")

        order_tool = registry.get("order")

        payment_method = order_payment_method or "not_provided"
        delivery_mode = order_delivery_mode or "not_provided"

        tool_result = order_tool.call(
            ctx,
            items=order_items,
            payment_method=payment_method,
            delivery_mode=delivery_mode,
            special_instructions=order_special_instructions,
            table_number=order_table_number,
        )

        data = tool_result.data or {}
        if not tool_result.success or not data:
            reply_text = (
                "I tried to place your order with the ordering service, "
                "but it did not return a valid response. Please try again or contact staff."
            )
            return FlowServiceResult(reply_text=reply_text, route="order_error")

        order_id = data.get("order_id", "unknown")
        status = data.get("status", "pending")
        eta = data.get("eta_minutes")
        total = data.get("total_amount")
        currency = data.get("currency")

        parts = [f"Your order {order_id} is {status}."]
        if eta is not None:
            parts.append(f"Estimated time: {eta} minutes.")
        if total is not None and currency:
            parts.append(f"Total: {total} {currency}.")

        reply_text = " ".join(parts) or "Your order has been processed."
        return FlowServiceResult(reply_text=reply_text, route="order")

    if intent == "recommend":
        recommend_tool = registry.get("recommend")
        tool_result = recommend_tool.call(ctx, context=text)

        data = tool_result.data or {}
        recos = data.get("recommendations", [])

        if not recos:
            reply_text = (
                "I could not generate any recommendations right now. "
                "Please try again later or ask for the menu."
            )
            return FlowServiceResult(reply_text=reply_text, route="recommend_empty")

        lines = ["Here are some recommendations:"]
        for idx, item in enumerate(recos, start=1):
            name = item.get("name", "Item")
            price = item.get("price")
            currency = item.get("currency")
            reason = item.get("reason")

            base = f"{idx}. {name}"
            if price is not None and currency:
                base += f" – {price} {currency}"
            if reason:
                base += f" ({reason})"
            lines.append(base)

        reply_text = "\n".join(lines)
        return FlowServiceResult(reply_text=reply_text, route="recommend")

    if intent == "track_order":
        if not tracking_order_id:
            reply_text = (
                "I can track your order, but I don't know which order ID to use.\n\n"
                "Please provide your order ID (for example: 'Track order ORD-12345')."
            )
            return FlowServiceResult(reply_text=reply_text, route="track_missing_order_id")

        tracking_tool = registry.get("tracking")
        tool_result = tracking_tool.call(ctx, order_id=tracking_order_id)

        data = tool_result.data or {}
        if not tool_result.success or not data:
            reply_text = (
                f"I tried to look up order {tracking_order_id}, but the tracking service "
                "did not return any information. Please verify your order ID or try again later."
            )
            return FlowServiceResult(reply_text=reply_text, route="track_error")

        order_id = data.get("order_id", tracking_order_id)
        status = data.get("status", "pending")
        eta = data.get("eta_minutes")

        parts = [f"Order {order_id} is currently {status}."]
        if eta is not None:
            parts.append(f"Estimated time remaining: {eta} minutes.")

        reply_text = " ".join(parts)
        return FlowServiceResult(reply_text=reply_text, route="track_order")

    if intent == "profile":
        profile_tool = registry.get("profile")
        tool_result = profile_tool.call(ctx, mode="get_profile")

        data = tool_result.data or {}
        prefs = data.get("preferences", {})
        hist = data.get("order_history_summary", {})

        lines = ["Here is what I know about your profile:"]

        dietary = prefs.get("dietary") or []
        spice = prefs.get("spice_level")
        allergies = prefs.get("allergies") or []

        if dietary:
            lines.append(f"- Dietary preferences: {', '.join(dietary)}")
        if spice:
            lines.append(f"- Preferred spice level: {spice}")
        if allergies:
            lines.append(f"- Allergies: {', '.join(allergies)}")

        total_orders = hist.get("total_orders")
        favorite_items = hist.get("favorite_items") or []
        avg_spend = hist.get("avg_spend")

        if total_orders is not None:
            lines.append(f"- Total orders: {total_orders}")
        if favorite_items:
            lines.append(f"- Favorite items: {', '.join(favorite_items)}")
        if avg_spend is not None:
            lines.append(f"- Average spend: {avg_spend}")

        if len(lines) == 1:
            lines.append("No detailed profile information is available yet.")

        reply_text = "\n".join(lines)
        return FlowServiceResult(reply_text=reply_text, route="profile")

    reply_text = (
        "I can help you by reading the menu, placing orders, recommending dishes, "
        "tracking your order, or showing your profile.\n\n"
        "Try things like:\n"
        "- 'Read me the menu'\n"
        "- 'I want to order Garlic Chicken'\n"
        "- 'What do you recommend?'\n"
        "- 'Where is my order ORD-12345?'\n"
        "- 'Remember that I do not eat pork'\n\n"
        f"(You said: {text})"
    )

    loki.log(
        "info",
        {
            "event_type": "flow_fallback",
            "intent": intent,
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "trace_id": trace_id,
        },
        service_type="flow_service",
        sync_mode="sync",
        io="none",
    )

    return FlowServiceResult(reply_text=reply_text, route="fallback")

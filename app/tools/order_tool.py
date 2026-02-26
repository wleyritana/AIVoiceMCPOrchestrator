from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.tools.base_tool import BaseTool, ToolCallContext, ToolResult
from app.services.order_service import place_order


class OrderTool(BaseTool):
    name = "order"

    def call(
        self,
        ctx: ToolCallContext,
        items: List[Dict[str, Any]],
        payment_method: str,
        delivery_mode: str,
        special_instructions: Optional[str] = None,
        table_number: Optional[str] = None,
    ) -> ToolResult:
        payload = place_order(
            user_id=ctx.user_id,
            channel=ctx.channel,
            session_id=ctx.session_id,
            items=items,
            payment_method=payment_method,
            delivery_mode=delivery_mode,
            special_instructions=special_instructions,
            table_number=table_number,
            trace_id=ctx.trace_id,
        )
        return ToolResult(success=bool(payload), data=payload)

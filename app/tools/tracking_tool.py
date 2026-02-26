from __future__ import annotations

from app.tools.base_tool import BaseTool, ToolCallContext, ToolResult
from app.services.tracking_service import get_order_status


class TrackingTool(BaseTool):
    name = "tracking"

    def call(self, ctx: ToolCallContext, order_id: str, **kwargs) -> ToolResult:
        payload = get_order_status(
            user_id=ctx.user_id,
            channel=ctx.channel,
            session_id=ctx.session_id,
            order_id=order_id,
            trace_id=ctx.trace_id,
        )
        return ToolResult(success=bool(payload), data=payload)

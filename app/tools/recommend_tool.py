from __future__ import annotations

from typing import Optional

from app.tools.base_tool import BaseTool, ToolCallContext, ToolResult
from app.services.recommend_service import get_recommendations


class RecommendTool(BaseTool):
    name = "recommend"

    def call(self, ctx: ToolCallContext, context: Optional[str] = None, **kwargs) -> ToolResult:
        payload = get_recommendations(
            user_id=ctx.user_id,
            channel=ctx.channel,
            session_id=ctx.session_id,
            context=context,
            trace_id=ctx.trace_id,
        )
        return ToolResult(success=bool(payload), data=payload)

from __future__ import annotations

from typing import Optional, Dict, Any

from app.tools.base_tool import BaseTool, ToolCallContext, ToolResult
from app.services.customer_profile_service import (
    get_user_profile,
    save_user_preferences,
)


class CustomerProfileTool(BaseTool):
    name = "profile"

    def call(
        self,
        ctx: ToolCallContext,
        mode: str = "get_profile",
        preferences: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        if mode == "save_preferences" and preferences is not None:
            payload = save_user_preferences(
                user_id=ctx.user_id,
                channel=ctx.channel,
                session_id=ctx.session_id,
                preferences=preferences,
                trace_id=ctx.trace_id,
            )
        else:
            payload = get_user_profile(
                user_id=ctx.user_id,
                channel=ctx.channel,
                session_id=ctx.session_id,
                trace_id=ctx.trace_id,
            )
        return ToolResult(success=bool(payload), data=payload)

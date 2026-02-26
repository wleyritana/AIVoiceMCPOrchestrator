from __future__ import annotations

from app.tools.base_tool import BaseTool, ToolCallContext, ToolResult
from app.services.menu_service import fetch_menu


class MenuTool(BaseTool):
    name = "menu"

    def call(self, ctx: ToolCallContext, **kwargs) -> ToolResult:
        menu_payload = fetch_menu(
            user_id=ctx.user_id,
            channel=ctx.channel,
            session_id=ctx.session_id,
            trace_id=ctx.trace_id,
        )

        text = ""
        if isinstance(menu_payload, dict):
            if isinstance(menu_payload.get("output"), str):
                text = menu_payload["output"].strip()
            elif "categories" in menu_payload:
                lines = []
                for c in menu_payload["categories"] or []:
                    name = c.get("name", "Category")
                    items = c.get("items") or []
                    item_names = ", ".join(i.get("name", "") for i in items if isinstance(i, dict))
                    if item_names:
                        lines.append(f"{name}: {item_names}")
                    else:
                        lines.append(name)
                if lines:
                    text = "Here is the menu:\n" + "\n".join(lines)

        return ToolResult(success=bool(text), data=menu_payload, raw_text=text or None)

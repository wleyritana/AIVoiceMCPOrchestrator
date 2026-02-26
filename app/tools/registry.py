from __future__ import annotations

from typing import Dict

from app.tools.base_tool import BaseTool
from app.tools.menu_tool import MenuTool
from app.tools.order_tool import OrderTool
from app.tools.recommend_tool import RecommendTool
from app.tools.tracking_tool import TrackingTool
from app.tools.profile_tool import CustomerProfileTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self.register(MenuTool())
        self.register(OrderTool())
        self.register(RecommendTool())
        self.register(TrackingTool())
        self.register(CustomerProfileTool())

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered")
        return self._tools[name]


_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _registry

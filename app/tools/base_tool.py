from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolCallContext:
    user_id: str
    channel: str
    session_id: str
    trace_id: Optional[str] = None


@dataclass
class ToolResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None
    error: Optional[str] = None


class BaseTool:
    name: str = "base"

    def call(self, ctx: ToolCallContext, **kwargs) -> ToolResult:
        raise NotImplementedError

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.observability.logging_loki import loki
from app.intent.intent_service import classify_intent
from app.flows.flow_service import run_flow, FlowServiceResult
from app.session.session_manager import get_session


class OrchestrateRequest(BaseModel):
    text: str
    user_id: str
    channel: str = "web"
    session_id: Optional[str] = None
    trace_id: Optional[str] = None

    order_items: Optional[List[Dict[str, Any]]] = None
    order_payment_method: Optional[str] = None
    order_delivery_mode: Optional[str] = None
    order_special_instructions: Optional[str] = None
    order_table_number: Optional[str] = None

    tracking_order_id: Optional[str] = None


class OrchestrateResponse(BaseModel):
    decision: str
    reply_text: str
    session_id: str
    route: str
    intent: str
    intent_confidence: float
    trace_id: Optional[str] = None


app = FastAPI(title="Blinksbuy MCP Orchestrator v2 – Production Safe (Phase 6)")


@app.get("/health")
def health_check():
    loki.log(
        "info",
        {"event_type": "health"},
        service_type="orchestrator",
        sync_mode="sync",
        io="none",
    )
    return {"status": "ok", "service": "mcp_orchestrator_v2_phase6"}


@app.post("/orchestrate", response_model=OrchestrateResponse)
def orchestrate(req: OrchestrateRequest):

    start = time.perf_counter()

    session_id = req.session_id or f"{req.user_id}:{req.channel}"
    state = get_session(session_id)
    state.turn_count += 1
    state.last_active_at = datetime.now(timezone.utc)

    trace_id = req.trace_id or f"trace-{session_id}-{state.turn_count}"

    intent_result = classify_intent(
        text=req.text,
        user_id=req.user_id,
        channel=req.channel,
        session_id=session_id,
        history=None,
        trace_id=trace_id,
    )
    intent = intent_result.intent
    confidence = intent_result.confidence

    loki.log(
        "info",
        {
            "event_type": "input",
            "user": req.user_id,
            "channel": req.channel,
            "session_id": session_id,
            "turn": state.turn_count,
            "intent": intent,
            "intent_confidence": confidence,
            "text": req.text,
            "trace_id": trace_id,
            "has_order_items": bool(req.order_items),
            "has_tracking_order_id": bool(req.tracking_order_id),
        },
        service_type="orchestrator",
        sync_mode="sync",
        io="in",
    )

    try:
        flow_result: FlowServiceResult = run_flow(
            intent=intent,
            text=req.text,
            user_id=req.user_id,
            channel=req.channel,
            session_id=session_id,
            trace_id=trace_id,
            order_items=req.order_items,
            order_payment_method=req.order_payment_method,
            order_delivery_mode=req.order_delivery_mode,
            order_special_instructions=req.order_special_instructions,
            order_table_number=req.order_table_number,
            tracking_order_id=req.tracking_order_id,
        )

        reply_text = flow_result.reply_text
        route = flow_result.route

        latency_ms = round((time.perf_counter() - start) * 1000.0, 3)

        loki.log(
            "info",
            {
                "event_type": "output",
                "user": req.user_id,
                "channel": req.channel,
                "session_id": session_id,
                "turn": state.turn_count,
                "latency_ms": latency_ms,
                "route": route,
                "intent": intent,
                "intent_confidence": confidence,
                "message": "request_end",
                "trace_id": trace_id,
            },
            service_type="orchestrator",
            sync_mode="sync",
            io="out",
        )

        return OrchestrateResponse(
            decision="reply",
            reply_text=reply_text,
            session_id=session_id,
            route=route,
            intent=intent,
            intent_confidence=confidence,
            trace_id=trace_id,
        )

    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000.0, 3)

        loki.log(
            "error",
            {
                "event_type": "error",
                "user": req.user_id,
                "channel": req.channel,
                "session_id": session_id,
                "turn": state.turn_count,
                "latency_ms": latency_ms,
                "intent": intent,
                "intent_confidence": confidence,
                "error": str(e),
                "trace_id": trace_id,
            },
            service_type="orchestrator",
            sync_mode="sync",
            io="none",
        )

        raise HTTPException(status_code=500, detail="Internal error in orchestrator")

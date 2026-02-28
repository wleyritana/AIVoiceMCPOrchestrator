"""app/llm_service.py

Thin wrapper around OpenAI Chat Completions for ClinicOps drafting.

Design goals:
- Keep the orchestrator logic unchanged (intent -> flow -> reply).
- Centralize LLM calls so flows stay readable.
- Provide safe fallbacks when OPENAI_API_KEY is not configured.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from openai import OpenAI

from .logging_loki import loki


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


client: Optional[OpenAI] = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


def _no_key_message(kind: str) -> str:
    return (
        f"ClinicOps '{kind}' drafting requires OPENAI_API_KEY. "
        "Set OPENAI_API_KEY (and optionally OPENAI_MODEL) in your Railway/GitHub environment.\n\n"
        "Example: export OPENAI_API_KEY=..."
    )


# -------------------------------------------------------------------
# Unified EMS prompt (SOAP + Assessment + Plan in one output)
# Keep lightweight and action-oriented for time-sensitive workflows.
# -------------------------------------------------------------------
EMS_UNIFIED_PROMPT = """
You are a clinician-facing EMS documentation and reasoning assistant.

Convert paramedic field notes into a structured, chart-ready SOAP note focused on time-sensitive decision-making.

Language:
- Default: English.
- Swedish only if explicitly requested.

Rules:
- Do not invent facts. If missing, write "Not provided."
- Preserve timelines and scene details.
- Clinician-facing only.
- No definitive medication dosing.
- Do not repeat content between sections.
- Handle fragmented dictation clearly and concisely.

Output:

Title: "SOAP Note (Draft)"

Sections:
Chief Complaint
HPI
ROS (if present)
PMH/PSH (if known)
Medications (if known)
Allergies (if known)
Vitals
Physical Exam (field findings)
Assessment
Plan
Gaps to Confirm

Assessment:
- Prioritize life-threatening causes first.
- Highlight time-sensitive conditions.
- Include ranked differential (max 5, 1 sentence each).
- Clearly state red flags.
- Use cautious language if uncertain.

Plan:
- Action-oriented bullets.
- Immediate stabilization steps (no dosing).
- Monitoring priorities.
- Transport decision and urgency.
- Pre-arrival notification if relevant.

Optional — Next Steps:
Only if requested.
- Max 5 bullets, ≤12 words each.
- Focus on immediate field actions and escalation triggers.

Optional — Patient Summary:
Only if requested.
- Plain language.
- Max 100 words.
- No differential or clinician reasoning.

End with:
Draft for clinician review.
""".strip()


def _run_llm(messages: list[dict], temperature: float) -> str:
    """Single place to call OpenAI; keeps the rest of the file stable."""
    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return (completion.choices[0].message.content or "").strip()


def draft_documentation_note(
    text: str,
    user_id: str,
    channel: str,
    session_id: str,
    trace_id: Optional[str] = None,
) -> str:
    """Generate a structured clinician note (SOAP + Assessment + Plan) from raw notes."""

    if client is None:
        return _no_key_message("documentation")

    start = time.perf_counter()

    # Unified EMS prompt: generates SOAP + Assessment + Plan in one call
    messages = [
        {"role": "system", "content": EMS_UNIFIED_PROMPT},
        {"role": "user", "content": text},
    ]

    loki.log(
        "info",
        {
            "event_type": "service_call",
            "reason": "draft_documentation_note",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
        },
        service_type="llm_service",
        sync_mode="async",
        io="out",
        trace_id=trace_id,
    )

    # Keep temperature as originally used for documentation (low variance)
    content = _run_llm(messages, temperature=0.2)

    latency_ms = round((time.perf_counter() - start) * 1000.0, 3)

    loki.log(
        "info",
        {
            "event_type": "service_return",
            "reason": "draft_documentation_note",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "latency_ms": latency_ms,
            "chars": len(content),
        },
        service_type="llm_service",
        sync_mode="async",
        io="in",
        trace_id=trace_id,
    )

    return content or "(No content returned.)"


def draft_assessment_plan(
    text: str,
    user_id: str,
    channel: str,
    session_id: str,
    trace_id: Optional[str] = None,
) -> str:
    """Generate a clinician-facing draft Assessment & Plan (now unified SOAP + A&P for EMS)."""

    if client is None:
        return _no_key_message("assessment_plan")

    start = time.perf_counter()

    # Same unified prompt to make workflow seamless and avoid repeating notes
    messages = [
        {"role": "system", "content": EMS_UNIFIED_PROMPT},
        {"role": "user", "content": text},
    ]

    loki.log(
        "info",
        {
            "event_type": "service_call",
            "reason": "draft_assessment_plan",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
        },
        service_type="llm_service",
        sync_mode="async",
        io="out",
        trace_id=trace_id,
    )

    # Keep original A&P temperature (slightly higher) OR set to 0.2 for consistency.
    # Leaving as 0.3 preserves previous behavior (more flexible reasoning).
    content = _run_llm(messages, temperature=0.3)

    latency_ms = round((time.perf_counter() - start) * 1000.0, 3)

    loki.log(
        "info",
        {
            "event_type": "service_return",
            "reason": "draft_assessment_plan",
            "user": user_id,
            "channel": channel,
            "session_id": session_id,
            "latency_ms": latency_ms,
            "chars": len(content),
        },
        service_type="llm_service",
        sync_mode="async",
        io="in",
        trace_id=trace_id,
    )

    return content or "(No content returned.)"

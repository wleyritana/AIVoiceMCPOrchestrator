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


def draft_documentation_note(
    text: str,
    user_id: str,
    channel: str,
    session_id: str,
    trace_id: Optional[str] = None,
) -> str:
    """Generate a structured clinician note (SOAP/H&P/etc.) from raw notes."""

    if client is None:
        return _no_key_message("documentation")

    start = time.perf_counter()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a clinician-facing documentation assistant. "
                "Your job is to transform clinician-provided notes into a clean, paste-ready clinical note.\n\n"
                "Rules:\n"
                "- Do NOT invent facts. If a section is missing, write 'Not provided.'\n"
                "- Preserve negations (e.g., denies X) and timelines.\n"
                "- Keep content clinician-facing (no patient-directed advice).\n"
                "- Keep medication doses/general guidelines as reminders only; do not output definitive dosing.\n\n"
                "Output format:\n"
                "1) Title: 'SOAP Note (Draft)' unless the input explicitly requests H&P, progress note, discharge summary, or consult note.\n"
                "2) Sections: Chief Complaint, HPI, ROS (only if present), PMH/PSH, Medications, Allergies, Social/Family History (if present), Vitals, Physical Exam, Assessment, Plan, Gaps to Confirm.\n"
                "3) End with: 'Draft for clinician review.'"
            ),
        },
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

    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.2,
    )

    content = (completion.choices[0].message.content or "").strip()
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
    """Generate a clinician-facing draft Assessment & Plan from a case vignette."""

    if client is None:
        return _no_key_message("assessment_plan")

    start = time.perf_counter()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a clinician-facing clinical reasoning copilot. "
                "Given a patient presentation, produce a *draft* assessment and plan for clinician review.\n\n"
                "Rules:\n"
                "- Anchor to the provided facts only; do NOT invent vitals, exam findings, or history.\n"
                "- If key info is missing, list it under 'Questions to Clarify' instead of guessing.\n"
                "- Use careful language (e.g., 'consider', 'suggest', 'evaluate').\n"
                "- Do not provide definitive medication dosing.\n\n"
                "Output structure:\n"
                "- Clinical Summary (1 paragraph)\n"
                "- Immediate Concerns / Red Flags (if any)\n"
                "- Differential (ranked, with 1–2 sentence justification each)\n"
                "- Recommended Workup (questions, exam focus, labs/imaging)\n"
                "- Initial Management (high-level, clinician-facing)\n"
                "- Disposition / Follow-up Considerations\n"
                "- Questions to Clarify\n"
                "End with: 'Draft for clinician review.'"
            ),
        },
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

    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.3,
    )

    content = (completion.choices[0].message.content or "").strip()
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

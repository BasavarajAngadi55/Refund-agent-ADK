"""LLM-as-judge eval scorer using Groq (via LiteLLM)."""

from __future__ import annotations

import json
import os
import re

from litellm import completion

DEFAULT_JUDGE_MODEL = os.getenv(
    "GROQ_JUDGE_MODEL",
    os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
)


def _parse_judge_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def evaluate(instance: dict, *, groq_api_key: str | None = None) -> dict:
    """Score agent reply text against an optional judge_rubric."""
    api_key = groq_api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        return {
            "score": 0.0,
            "explanation": "GROQ_API_KEY not set — required for LLM judge",
        }

    rubric = instance.get("judge_rubric") or (
        "The response should correctly address the refund request per retail policy."
    )
    prompt = instance.get("prompt", "")
    response = instance.get("response", "")

    if not response.strip():
        return {"score": 0.0, "explanation": "Empty agent response"}

    judge_prompt = f"""You are an evaluation judge for a retail refund assistant.

Policy context:
- Return window is 30 days from purchase (today is July 17, 2026).
- Clearance items are non-refundable.
- Order must exist before refund.
- Agent should explain clearly when refusing a refund.

User message:
{prompt}

Agent response:
{response}

Rubric for this test case:
{rubric}

Return JSON only:
{{"pass": true or false, "reason": "one sentence"}}
"""

    try:
        result = completion(
            model=f"groq/{DEFAULT_JUDGE_MODEL}",
            messages=[{"role": "user", "content": judge_prompt}],
            api_key=api_key,
            temperature=0,
        )
        raw = result.choices[0].message.content or ""
        parsed = _parse_judge_json(raw)
        passed = bool(parsed.get("pass"))
        return {
            "score": 1.0 if passed else 0.0,
            "explanation": str(parsed.get("reason") or raw).strip(),
        }
    except json.JSONDecodeError as exc:
        return {"score": 0.0, "explanation": f"Judge returned invalid JSON: {exc}"}
    except Exception as exc:
        return {"score": 0.0, "explanation": f"Judge error: {exc}"}

"""Local eval runner — tool trajectory + Groq LLM-as-judge.

Usage:
  cd retail-refund-agent
  source .venv/bin/activate
  export OLLAMA_API_BASE=http://localhost:11434
  export OLLAMA_MODEL=gemma4:e2b
  export GROQ_API_KEY=your_key          # judge only
  export GROQ_JUDGE_MODEL=llama-3.3-70b-versatile
  python tests/eval/run_local_eval.py

Notes:
  - Agent uses Ollama during eval (better tool calling than Groq).
  - Groq is used only for LLM-as-judge.
  - Database is reset before each case so refund state stays clean.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "tests/eval/evalsets/refund_cases.evalset.json"

load_dotenv(PROJECT_ROOT / ".env")

# Groq for judge only — agent uses Ollama (Groq tool-calls are flaky in ADK).
JUDGE_GROQ_KEY = os.getenv("GROQ_API_KEY")
os.environ.pop("GROQ_API_KEY", None)

sys.path.insert(0, str(PROJECT_ROOT))
from app.agent import root_agent  # noqa: E402
from app.database import init_db  # noqa: E402
from tests.eval.llm_judge import evaluate as score_judge  # noqa: E402
from tests.eval.tool_call_check import evaluate as score_tools  # noqa: E402


def load_cases() -> list[dict]:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = data.get("eval_cases") or []
    if not cases:
        raise SystemExit(f"No eval_cases in {DATASET}")
    return cases


def tool_names_from_events(events) -> list[str]:
    names: list[str] = []
    for event in events:
        if hasattr(event, "get_function_calls"):
            for fc in event.get_function_calls():
                if fc.name:
                    names.append(fc.name)
    return names


async def run_case(case: dict) -> dict:
    case_id = case.get("eval_case_id") or case.get("name") or "case"
    prompt = case.get("prompt", "")
    if isinstance(prompt, dict):
        parts = prompt.get("parts") or []
        prompt = " ".join(p.get("text", "") for p in parts if isinstance(p, dict))

    # Fresh order data every case (avoids "already refunded" from prior runs).
    init_db(force_reseed=True)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="local_eval",
        session_service=session_service,
    )
    session_id = case_id.replace(" ", "_")
    await session_service.create_session(
        app_name="local_eval",
        user_id="eval_user",
        session_id=session_id,
    )

    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    events = []
    response_text = ""
    run_error = ""

    try:
        async for event in runner.run_async(
            user_id="eval_user",
            session_id=session_id,
            new_message=msg,
        ):
            events.append(event)
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text or ""
    except Exception as exc:
        run_error = str(exc)

    tool_calls = tool_names_from_events(events)
    instance = {
        **case,
        "prompt": prompt,
        "response": response_text,
        "tool_calls": tool_calls,
    }
    tool_result = score_tools(instance)
    judge_result = score_judge(instance, groq_api_key=JUDGE_GROQ_KEY)
    overall_score = min(tool_result["score"], judge_result["score"])

    if run_error:
        overall_score = 0.0
        tool_result = {
            "score": 0.0,
            "explanation": f"Agent run failed: {run_error[:200]}",
        }

    return {
        "case_id": case_id,
        "prompt": prompt,
        "tool_calls": tool_calls,
        "response_preview": (
            (response_text[:200] + "...") if len(response_text) > 200 else response_text
        ),
        "tool_score": tool_result["score"],
        "tool_explanation": tool_result["explanation"],
        "judge_score": judge_result["score"],
        "judge_explanation": judge_result["explanation"],
        "overall_score": overall_score,
    }


async def main() -> int:
    if not JUDGE_GROQ_KEY:
        raise SystemExit("GROQ_API_KEY required in .env for LLM judge")

    print(f"Loading cases from {DATASET}")
    cases = load_cases()
    print(
        f"Running {len(cases)} case(s) — Ollama agent + Groq LLM judge "
        f"(DB reset per case)...\n"
    )

    results = []
    passed = 0
    for case in cases:
        case_id = case.get("eval_case_id", case.get("name"))
        print(f"--- {case_id} ---")
        result = await run_case(case)
        results.append(result)
        ok = result["overall_score"] >= 1.0
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"Tools called: {result['tool_calls']}")
        tool_status = "PASS" if result["tool_score"] >= 1.0 else "FAIL"
        judge_status = "PASS" if result["judge_score"] >= 1.0 else "FAIL"
        print(f"Tool check: {tool_status} — {result['tool_explanation']}")
        print(f"LLM judge: {judge_status} — {result['judge_explanation']}")
        print(f"Overall: {status}")
        print(f"Reply: {result['response_preview']}\n")

    print("=" * 60)
    print(f"SUMMARY: {passed}/{len(results)} passed (tools + LLM judge)")
    print("=" * 60)
    for r in results:
        mark = "PASS" if r["overall_score"] >= 1.0 else "FAIL"
        print(
            f"  [{mark}] {r['case_id']}: tools={r['tool_score']} judge={r['judge_score']}"
        )

    report_path = PROJECT_ROOT / "artifacts" / "local_eval_results.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"passed": passed, "total": len(results), "results": results}, indent=2),
        encoding="utf-8",
    )
    print(f"\nReport saved: {report_path}")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

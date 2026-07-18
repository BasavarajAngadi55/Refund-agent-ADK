"""Checks if agent called expected tools (deterministic, no cloud)."""


def evaluate(instance):
    actual = instance.get("tool_calls") or []
    if isinstance(actual, list) and actual and isinstance(actual[0], dict):
        actual = [t.get("name", t) for t in actual]

    expected = instance.get("expected_tool_calls") or []
    unexpected = instance.get("unexpected_tool_calls") or []

    score = 1.0
    parts = []

    for tool in expected:
        if tool not in actual:
            score = 0.0
            parts.append(f"Missing expected tool: {tool}")

    for tool in unexpected:
        if tool in actual:
            score = 0.0
            parts.append(f"Called forbidden tool: {tool}")

    if score == 1.0:
        parts.append(f"Tool trajectory OK: {actual}")

    return {"score": score, "explanation": "; ".join(parts) or "OK"}

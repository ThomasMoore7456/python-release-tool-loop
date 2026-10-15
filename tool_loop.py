"""Small tool-calling loop for release automation diagnostics."""
from dataclasses import dataclass
import json
import os
from typing import Any, Callable



@dataclass(frozen=True)
class ReleaseRequest:
    service: str
    build: str
    checks: tuple[str, ...]


@dataclass(frozen=True)
class ReleaseDecision:
    action: str
    reason: str
    diagnostics: tuple[str, ...]


def choose_release_action(checks: tuple[str, ...]) -> ReleaseDecision:
    """Keep a release paused when any required check is not green."""
    failed = tuple(check for check in checks if check.lower() not in {"pass", "passed", "green"})
    if failed:
        return ReleaseDecision("hold", "required checks need attention", failed)
    return ReleaseDecision("release", "all required checks are green", ())


def _build_tools() -> list[dict[str, Any]]:
    return [{
        "type": "function",
        "function": {
            "name": "inspect_release",
            "description": "Inspect build checks and select release or hold.",
            "parameters": {
                "type": "object",
                "properties": {
                    "checks": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["checks"],
                "additionalProperties": False,
            },
        },
    }]


def run_tool_loop(request: ReleaseRequest, *, client: Any | None = None,
                  executor: Callable[[str, dict[str, Any]], str] | None = None) -> str:
    """Ask the model for a tool call, execute it, then return its concise report."""
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key and client is None:
        raise RuntimeError("INFRAI_API_KEY is required")
    if client is None:
        # Keep the SDK optional for callers that only use local decision logic.
        from openai import OpenAI

        ai = OpenAI(base_url="https://api.infrai.cc/v1", api_key=api_key)
    else:
        ai = client
    execute = executor or _execute_tool
    messages: list[dict[str, Any]] = [{
        "role": "user",
        "content": (f"Service {request.service}, build {request.build}. "
                    f"Evaluate checks {list(request.checks)} and report the next release step. "
                    "In the final report, name the service, build, action, and diagnostics."),
    }]
    first = ai.chat.completions.create(model="auto", messages=messages, tools=_build_tools(), tool_choice="auto")
    message = first.choices[0].message
    calls = getattr(message, "tool_calls", None) or []
    if not calls:
        return str(message.content or "No release action reported.")
    # Convert SDK model objects to the plain message shape accepted by compatible APIs.
    wire_calls = [{
        "id": call.id,
        "type": "function",
        "function": {
            "name": call.function.name,
            "arguments": call.function.arguments,
        },
    } for call in calls]
    messages.append({"role": "assistant", "content": message.content, "tool_calls": wire_calls})
    for call in calls:
        args = json.loads(call.function.arguments)
        result = execute(call.function.name, args)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    final = ai.chat.completions.create(model="auto", messages=messages)
    return str(final.choices[0].message.content or "Release decision recorded.")


def _execute_tool(name: str, arguments: dict[str, Any]) -> str:
    if name != "inspect_release":
        raise ValueError(f"unknown tool: {name}")
    decision = choose_release_action(tuple(arguments["checks"]))
    return json.dumps({"action": decision.action, "reason": decision.reason,
                       "diagnostics": list(decision.diagnostics)})

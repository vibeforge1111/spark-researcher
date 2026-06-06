from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterSpec:
    name: str
    supports_native_prehook: bool
    supports_tool_context: bool
    max_advisory_chars: int
    injection_mode: str


def _brief(advisory: dict[str, Any], max_chars: int) -> str:
    lines = ["Advisory Brief", ""]
    epistemic = advisory.get("epistemic_status", {})
    if isinstance(epistemic, dict):
        status = str(epistemic.get("status") or "").strip()
        if status:
            lines.append(f"Evidence Status: {status}")
        packet_stability = epistemic.get("packet_stability", {})
        if isinstance(packet_stability, dict):
            stability_status = str(packet_stability.get("status") or "").strip()
            if stability_status:
                lines.append(f"Packet Stability: {stability_status}")
            durable = int(packet_stability.get("durable_belief_count") or 0)
            provisional = int(packet_stability.get("provisional_belief_count") or 0)
            contradictions = int(packet_stability.get("contradiction_count") or 0)
            if durable or provisional or contradictions:
                lines.append(
                    f"- belief mix: durable={durable}, provisional={provisional}, contradictions={contradictions}"
                )
        for item in epistemic.get("missing_evidence", [])[:2]:
            lines.append(f"- Missing: {item}")
        next_questions = epistemic.get("clarifying_questions", [])
        if next_questions:
            lines.extend(["", "Questions Before Strong Claims"])
            for item in next_questions[:2]:
                lines.append(f"- {item}")
        lines.append("")
    intent = advisory.get("intent", {})
    if isinstance(intent, dict) and intent.get("active"):
        goal = str(intent.get("goal") or "").strip()
        outcome = str(intent.get("outcome") or "").strip()
        criteria = [str(item) for item in intent.get("success_criteria", [])][:3]
        if goal:
            lines.append(f"Goal: {goal}")
        if outcome:
            lines.append(f"Target Outcome: {outcome}")
        if criteria:
            lines.extend(["", "Success Criteria"])
            for item in criteria:
                lines.append(f"- {item}")
        lines.append("")
    for item in advisory.get("guidance", [])[:4]:
        lines.append(f"- {item}")
    boundaries = advisory.get("boundaries", [])
    if boundaries:
        lines.extend(["", "Boundaries"])
        for item in boundaries[:3]:
            lines.append(f"- {item}")
    failure_priorities = advisory.get("failure_priorities", {})
    if isinstance(failure_priorities, dict) and failure_priorities.get("priorities"):
        lines.extend(["", "Current Surprise Priorities"])
        for item in failure_priorities.get("priorities", [])[:2]:
            domain = str(item.get("domain") or "generic")
            surface = str(item.get("surface") or "unknown")
            score = item.get("surprise_score")
            lines.append(f"- {domain} / {surface} surprise={score}")
    text = "\n".join(lines).strip()
    return text[:max_chars].rstrip()


def _wrapper_request(spec: AdapterSpec, task: str, advisory: dict[str, Any]) -> dict[str, Any]:
    brief = _brief(advisory, spec.max_advisory_chars)
    return {
        "model_family": spec.name,
        "supports_native_prehook": spec.supports_native_prehook,
        "supports_tool_context": spec.supports_tool_context,
        "injection_mode": spec.injection_mode,
        "system_prompt": "",
        "user_prompt": f"{brief}\n\nTask\n\n{task}".strip(),
    }


def _native_request(spec: AdapterSpec, task: str, advisory: dict[str, Any]) -> dict[str, Any]:
    brief = _brief(advisory, spec.max_advisory_chars)
    return {
        "model_family": spec.name,
        "supports_native_prehook": spec.supports_native_prehook,
        "supports_tool_context": spec.supports_tool_context,
        "injection_mode": spec.injection_mode,
        "system_prompt": brief,
        "user_prompt": task,
    }


def _specs() -> dict[str, AdapterSpec]:
    return {
        "claude": AdapterSpec("claude", True, True, 2200, "native-prehook"),
        "codex": AdapterSpec("codex", False, True, 1800, "wrapper-preamble"),
        "openclaw": AdapterSpec("openclaw", False, True, 1800, "wrapper-preamble"),
        "generic": AdapterSpec("generic", False, False, 1600, "wrapper-preamble"),
    }


def adapter_names() -> list[str]:
    return sorted(_specs().keys())


def adapter_status() -> dict[str, Any]:
    return {"adapters": [asdict(item) for item in _specs().values()]}


def adapter_request(name: str, task: str, advisory: dict[str, Any]) -> dict[str, Any]:
    spec = _specs().get(name)
    if spec is None:
        raise RuntimeError(f"Unknown adapter: {name}. Known adapters: {', '.join(adapter_names())}.")
    if spec.supports_native_prehook:
        return _native_request(spec, task, advisory)
    return _wrapper_request(spec, task, advisory)

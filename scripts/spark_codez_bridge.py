#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def main() -> None:
    request = _read_request()
    response = _handle_request(request)
    _write_bridge_artifacts(request, response)
    print(json.dumps(response, sort_keys=True))


def _read_request() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("spark_codez_bridge.py expects a JSON request on stdin.")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"spark_codez_bridge.py received malformed JSON on stdin (first 80 chars: {raw[:80]!r}): {exc.msg}"
        ) from exc
    if not isinstance(parsed, dict):
        raise SystemExit("Spark Codez bridge request must be a JSON object.")
    return parsed


def _handle_request(request: dict[str, Any]) -> dict[str, Any]:
    try:
        from spark_researcher.advisory import build_advisory

        user_message = str(request.get("userMessage") or "").strip()
        if not user_message:
            return _controlled_response(request, "Spark Researcher bridge received an empty userMessage.")
        config_path = _resolve_config_path(request)
        domain = _infer_domain(request)
        advisory = build_advisory(config_path, user_message, model="generic", limit=4, domain=domain)
        return _response_from_advisory(request, advisory)
    except Exception as exc:
        return _controlled_response(
            request,
            "Spark Researcher bridge returned a controlled failure.",
            evidence=[f"{type(exc).__name__}: {exc}"],
            followup=["Inspect spark-researcher scripts/spark_codez_bridge.py and project config."],
        )


def _resolve_config_path(request: dict[str, Any]) -> Path:
    explicit = str(request.get("configPath") or "").strip()
    if explicit:
        return Path(explicit).resolve()
    runtime_root = Path(str(request.get("runtimeRoot") or REPO_ROOT)).resolve()
    return runtime_root / "spark-researcher.project.json"


def _infer_domain(request: dict[str, Any]) -> str | None:
    explicit = str(request.get("activeSpecializationPath") or "").strip().lower()
    if explicit:
        return _domain_from_key(explicit)
    chips = request.get("activeDomainChips") or []
    if isinstance(chips, list):
        for chip in chips:
            domain = _domain_from_key(str(chip).lower())
            if domain:
                return domain
    return None


def _domain_from_key(value: str) -> str | None:
    if not value:
        return None
    cleaned = value.replace("chip:", "").replace("domain-chip-", "")
    if cleaned.startswith("startup"):
        return "startup"
    if cleaned.startswith("xcontent") or "content" in cleaned:
        return "content"
    if "trading" in cleaned or "crypto" in cleaned:
        return "trading"
    if "growth" in cleaned:
        return "growth"
    if "memory" in cleaned:
        return "memory"
    first = cleaned.split("-", 1)[0].strip()
    return first or None


def _response_from_advisory(request: dict[str, Any], advisory: dict[str, Any]) -> dict[str, Any]:
    epistemic = _dict(advisory.get("epistemic_status"))
    packet_stability = _dict(advisory.get("packet_stability"))
    status = str(epistemic.get("status") or "unknown")
    guidance = _string_list(advisory.get("guidance"))[:4]
    boundaries = _string_list(advisory.get("boundaries"))[:3]
    missing = _string_list(epistemic.get("missing_evidence"))[:3]
    recommended = _string_list(epistemic.get("recommended_actions"))[:4]
    questions = _string_list(epistemic.get("clarifying_questions"))[:2]
    packet_refs = [str(item) for item in advisory.get("selected_packet_ids") or []][:8]
    packet_paths = [
        str(packet.get("path"))
        for packet in advisory.get("packets") or []
        if isinstance(packet, dict) and packet.get("path")
    ][:8]
    evidence_summary = [
        f"epistemic_status={status}",
        f"domain={advisory.get('domain', 'generic')}",
        f"packet_count={epistemic.get('packet_count', len(packet_refs))}",
        f"packet_stability={packet_stability.get('status', 'unknown')}",
        *[f"guidance: {item}" for item in guidance],
        *[f"boundary: {item}" for item in boundaries],
        *[f"missing: {item}" for item in missing],
    ]
    followup_actions = [*recommended, *[f"Clarify: {item}" for item in questions]]
    return {
        "requestId": str(request.get("requestId") or ""),
        "replyText": _reply_text(status, guidance, boundaries, missing),
        "evidenceSummary": evidence_summary[:12],
        "packetRefs": packet_refs,
        "memoryRefs": packet_paths,
        "escalationHint": _escalation_hint(str(request.get("userMessage") or ""), status),
        "followupActions": followup_actions[:6],
        "traceRef": str(advisory.get("trace_id") or request.get("traceId") or ""),
    }


def _reply_text(status: str, guidance: list[str], boundaries: list[str], missing: list[str]) -> str:
    parts = [f"Spark Researcher advisory is {status}."]
    if guidance:
        parts.append("Use: " + "; ".join(guidance[:2]))
    if boundaries:
        parts.append("Boundary: " + "; ".join(boundaries[:1]))
    if missing:
        parts.append("Missing evidence: " + "; ".join(missing[:2]))
    return " ".join(parts)


def _escalation_hint(user_message: str, status: str) -> str:
    lowered = user_message.lower()
    if any(term in lowered for term in ("deep research", "long-running", "latest", "fresh sources")):
        return "long-running_deep_research"
    if any(term in lowered for term in ("parallel", "multiple agents", "many repos")):
        return "parallelizable_subtasks"
    if any(term in lowered for term in ("cross-domain", "cross repo", "cross-repo")):
        return "cross-domain_or_cross-repo_work"
    if status in {"partial", "under_supported"}:
        return "needs_specialist_depth"
    return "none"


def _controlled_response(
    request: dict[str, Any],
    reply: str,
    *,
    evidence: list[str] | None = None,
    followup: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "requestId": str(request.get("requestId") or ""),
        "replyText": reply,
        "evidenceSummary": evidence or [],
        "packetRefs": [],
        "memoryRefs": [],
        "escalationHint": "none",
        "followupActions": followup or [],
        "traceRef": str(request.get("traceId") or ""),
    }


def _write_bridge_artifacts(request: dict[str, Any], response: dict[str, Any]) -> None:
    runtime_root = Path(str(request.get("runtimeRoot") or REPO_ROOT)).resolve()
    root = runtime_root / "artifacts" / "advisory" / "bridge-requests"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    request_meta = _request_artifact_metadata(request)
    response_meta = _response_artifact_metadata(response)
    (root / f"{stamp}.request.json").write_text(json.dumps(request_meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / f"{stamp}.response.json").write_text(json.dumps(response_meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _request_artifact_metadata(request: dict[str, Any]) -> dict[str, Any]:
    chips = request.get("activeDomainChips") if isinstance(request.get("activeDomainChips"), list) else []
    return {
        "schema_version": "spark.researcher.bridge_request_artifact.v1",
        "redaction": "metadata only; userMessage, prompt text, env values, and private payload bodies omitted",
        "requestId": str(request.get("requestId") or ""),
        "traceId": str(request.get("traceId") or ""),
        "hasUserMessage": bool(str(request.get("userMessage") or "").strip()),
        "userMessageLength": len(str(request.get("userMessage") or "")),
        "activeSpecializationPath": str(request.get("activeSpecializationPath") or ""),
        "activeDomainChipCount": len(chips),
        "runtimeRootConfigured": bool(str(request.get("runtimeRoot") or "").strip()),
        "configPathConfigured": bool(str(request.get("configPath") or "").strip()),
        "requestKeys": sorted(str(key) for key in request.keys()),
    }


def _response_artifact_metadata(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "spark.researcher.bridge_response_artifact.v1",
        "redaction": "metadata only; reply text, evidence text, memory bodies, and private payload bodies omitted",
        "requestId": str(response.get("requestId") or ""),
        "traceRef": str(response.get("traceRef") or ""),
        "replyTextLength": len(str(response.get("replyText") or "")),
        "evidenceSummaryCount": len(response.get("evidenceSummary") or []) if isinstance(response.get("evidenceSummary"), list) else 0,
        "packetRefCount": len(response.get("packetRefs") or []) if isinstance(response.get("packetRefs"), list) else 0,
        "memoryRefCount": len(response.get("memoryRefs") or []) if isinstance(response.get("memoryRefs"), list) else 0,
        "followupActionCount": len(response.get("followupActions") or []) if isinstance(response.get("followupActions"), list) else 0,
        "escalationHint": str(response.get("escalationHint") or "none"),
        "responseKeys": sorted(str(key) for key in response.keys()),
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


if __name__ == "__main__":
    main()

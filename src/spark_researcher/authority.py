from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable


ADVISORY_EXECUTE_TOOL_NAME = "researcher.advisory.execute"
ADVISORY_EXECUTE_OWNER_SYSTEM = "spark-researcher"
ADVISORY_EXECUTE_MUTATION_CLASS = "external_network"
ADVISORY_EXECUTE_ACTION_TYPE = "external_api_call"
ADVISORY_EXECUTE_CAPABILITY_ID = f"capability:{ADVISORY_EXECUTE_OWNER_SYSTEM}:{ADVISORY_EXECUTE_TOOL_NAME}"

_DEFAULT_MEMORY_WRITE_TOOL_NAME = "domain-chip-memory.memory.write"
_DEFAULT_MEMORY_WRITE_CAPABILITY_ID = "capability:domain-chip-memory:memory.write"
_DEFAULT_MEMORY_WRITE_ACTION_TYPE = "memory.write"

try:
    from domain_chip_memory import sdk as _domain_memory_sdk
except ModuleNotFoundError:
    _domain_memory_sdk = None

_DOMAIN_MEMORY_WRITE_TOOL_NAME = str(
    getattr(_domain_memory_sdk, "MEMORY_WRITE_TOOL_NAME", _DEFAULT_MEMORY_WRITE_TOOL_NAME)
)
_DOMAIN_MEMORY_WRITE_CAPABILITY_ID = str(
    getattr(_domain_memory_sdk, "MEMORY_WRITE_CAPABILITY_ID", _DEFAULT_MEMORY_WRITE_CAPABILITY_ID)
)
_DOMAIN_MEMORY_WRITE_ACTION_TYPE = str(
    getattr(_domain_memory_sdk, "MEMORY_WRITE_ACTION_TYPE", _DEFAULT_MEMORY_WRITE_ACTION_TYPE)
)

MEMORY_WRITE_TOOL_NAME = _DOMAIN_MEMORY_WRITE_TOOL_NAME
MEMORY_WRITE_OWNER_SYSTEM = "domain-chip-memory"
MEMORY_WRITE_MUTATION_CLASS = "writes_memory"
MEMORY_WRITE_ACTION_TYPE = _DOMAIN_MEMORY_WRITE_ACTION_TYPE
MEMORY_WRITE_CAPABILITY_ID = _DOMAIN_MEMORY_WRITE_CAPABILITY_ID

CHIP_CREATE_TOOL_NAME = "researcher.chip.create"
CHIP_CREATE_OWNER_SYSTEM = "spark-researcher"
CHIP_CREATE_MUTATION_CLASS = "creates_chip"
CHIP_CREATE_ACTION_TYPE = "create_domain_chip"
CHIP_CREATE_CAPABILITY_ID = f"capability:{CHIP_CREATE_OWNER_SYSTEM}:{CHIP_CREATE_TOOL_NAME}"

RUN_EXECUTION_TOOL_NAME = "researcher.run"
RUN_EXECUTION_OWNER_SYSTEM = "spark-researcher"
RUN_EXECUTION_MUTATION_CLASS = "writes_files"
RUN_EXECUTION_ACTION_TYPE = "edit_file"
RUN_EXECUTION_CAPABILITY_ID = f"capability:{RUN_EXECUTION_OWNER_SYSTEM}:{RUN_EXECUTION_TOOL_NAME}"

COLLECTIVE_PUBLISH_TOOL_NAME = "researcher.collective.publish"
COLLECTIVE_PUBLISH_OWNER_SYSTEM = "spark-researcher"
COLLECTIVE_PUBLISH_MUTATION_CLASS = "publishes"
COLLECTIVE_PUBLISH_ACTION_TYPE = "publish"
COLLECTIVE_PUBLISH_CAPABILITY_ID = f"capability:{COLLECTIVE_PUBLISH_OWNER_SYSTEM}:{COLLECTIVE_PUBLISH_TOOL_NAME}"

COLLECTIVE_SYNC_TOOL_NAME = "researcher.collective.sync-local"
COLLECTIVE_SYNC_OWNER_SYSTEM = "spark-researcher"
COLLECTIVE_SYNC_MUTATION_CLASS = "writes_files"
COLLECTIVE_SYNC_ACTION_TYPE = "edit_file"
COLLECTIVE_SYNC_CAPABILITY_ID = f"capability:{COLLECTIVE_SYNC_OWNER_SYSTEM}:{COLLECTIVE_SYNC_TOOL_NAME}"

COLLECTIVE_ABSORB_TOOL_NAME = "researcher.collective.absorb"
COLLECTIVE_ABSORB_OWNER_SYSTEM = "spark-researcher"
COLLECTIVE_ABSORB_MUTATION_CLASS = "publishes"
COLLECTIVE_ABSORB_ACTION_TYPE = "publish"
COLLECTIVE_ABSORB_CAPABILITY_ID = f"capability:{COLLECTIVE_ABSORB_OWNER_SYSTEM}:{COLLECTIVE_ABSORB_TOOL_NAME}"


def _harness_core_source_candidates() -> list[Path]:
    candidates: list[Path] = []
    candidates.append(Path(__file__).resolve().parents[3] / "spark-harness-core" / "src")
    spark_home = os.environ.get("SPARK_HOME")
    if spark_home:
        candidates.append(Path(spark_home).expanduser() / "modules" / "spark-harness-core" / "source" / "src")
    candidates.append(Path.home() / ".spark" / "modules" / "spark-harness-core" / "source" / "src")
    return candidates


def _load_verify_governor_tool_authority() -> Callable[..., dict[str, Any]]:
    try:
        from spark_harness_core.legacy_turn_intent import verify_governor_tool_authority

        return verify_governor_tool_authority
    except ModuleNotFoundError:
        pass

    for candidate in _harness_core_source_candidates():
        if not (candidate / "spark_harness_core" / "__init__.py").exists():
            continue
        candidate_text = str(candidate)
        if candidate_text not in sys.path:
            sys.path.insert(0, candidate_text)
        try:
            from spark_harness_core.legacy_turn_intent import verify_governor_tool_authority

            return verify_governor_tool_authority
        except ModuleNotFoundError:
            continue
    raise RuntimeError("spark_harness_core_unavailable")


def _load_harness_kernel_class() -> type[Any]:
    try:
        from spark_harness_core import HarnessKernel

        return HarnessKernel
    except ModuleNotFoundError:
        pass

    for candidate in _harness_core_source_candidates():
        if not (candidate / "spark_harness_core" / "__init__.py").exists():
            continue
        candidate_text = str(candidate)
        if candidate_text not in sys.path:
            sys.path.insert(0, candidate_text)
        try:
            from spark_harness_core import HarnessKernel

            return HarnessKernel
        except ModuleNotFoundError:
            continue
    raise RuntimeError("spark_harness_core_unavailable")


def _contains_string(payload: Any, needle: str) -> bool:
    if not needle:
        return True
    if isinstance(payload, dict):
        return any(_contains_string(key, needle) or _contains_string(value, needle) for key, value in payload.items())
    if isinstance(payload, (list, tuple, set)):
        return any(_contains_string(item, needle) for item in payload)
    return str(payload) == needle


def governor_decision_has_canonical_binding(governor_decision: dict[str, Any] | None) -> bool:
    if not isinstance(governor_decision, dict):
        return False
    evidence = governor_decision.get("evidence") if isinstance(governor_decision.get("evidence"), list) else []
    sources_by_kind = {
        str(item.get("kind") or ""): str(item.get("source") or "")
        for item in evidence
        if isinstance(item, dict)
    }
    return (
        sources_by_kind.get("policy") == "issuer:spark-harness-core/governor"
        and sources_by_kind.get("authority_binding_ref") == "provenance:spark-harness-core/authorization"
        and sources_by_kind.get("runtime_state") == "current-binding:spark-researcher"
    )


def memory_authority_ref(kind: str, value: str | Path) -> str:
    return f"spark-researcher.memory.{kind}:{Path(value) if isinstance(value, Path) else value}"


def memory_authority_refs(kind: str, *values: str | Path) -> tuple[str, ...]:
    refs = tuple(memory_authority_ref(kind, value) for value in values if str(value).strip())
    return refs or (f"spark-researcher.memory.{kind}",)


def require_advisory_execution_authority(
    governor_decision: dict[str, Any] | None,
    *,
    action_id: str | None = None,
) -> dict[str, Any]:
    verifier = _load_verify_governor_tool_authority()
    verification = verifier(
        governor_decision,
        tool_name=ADVISORY_EXECUTE_TOOL_NAME,
        owner_system=ADVISORY_EXECUTE_OWNER_SYSTEM,
        mutation_class=ADVISORY_EXECUTE_MUTATION_CLASS,
        external_network=True,
        action_id=action_id,
        require_pre_execution_ledger=True,
    )
    if not verification.get("allowed"):
        reasons = [str(item) for item in verification.get("reason_codes", []) if str(item).strip()]
        reason_text = ", ".join(reasons) if reasons else "governor_authority_denied"
        raise RuntimeError("Advisory execution requires GovernorDecisionV1 authority: " + reason_text)
    return verification


def require_memory_write_authority(
    governor_decision: dict[str, Any] | None,
    *,
    binding_refs: tuple[str, ...],
    action_id: str | None = None,
) -> dict[str, Any]:
    HarnessKernel = _load_harness_kernel_class()
    surface = "memory"
    if isinstance(governor_decision, dict) and str(governor_decision.get("surface") or "").strip():
        surface = str(governor_decision.get("surface") or "memory")
    kernel = HarnessKernel(surface=surface)
    verification = kernel.verify_governor_execution_authority(
        governor_decision,
        expected_capability_id=MEMORY_WRITE_CAPABILITY_ID,
        expected_action_type=MEMORY_WRITE_ACTION_TYPE,
        tool_name=MEMORY_WRITE_TOOL_NAME,
        action_id=action_id,
        require_pre_execution_ledger=True,
    )
    refs = tuple(ref for ref in binding_refs if str(ref).strip())
    if verification.get("allowed") and not refs:
        verification = {**verification, "allowed": False, "reason_codes": ["authority_binding_refs_missing"]}
    if verification.get("allowed"):
        missing_refs = [ref for ref in refs if not _contains_string(governor_decision, ref)]
        if missing_refs:
            verification = {
                **verification,
                "allowed": False,
                "reason_codes": ["authority_binding_missing", *missing_refs],
            }
    if verification.get("allowed") and not governor_decision_has_canonical_binding(governor_decision):
        verification = {**verification, "allowed": False, "reason_codes": ["canonical_governor_binding_missing"]}
    if not verification.get("allowed"):
        reasons = [str(item) for item in verification.get("reason_codes", []) if str(item).strip()]
        reason_text = ", ".join(reasons) if reasons else "governor_authority_denied"
        raise RuntimeError("Memory materialization requires GovernorDecisionV1 memory-write authority: " + reason_text)
    return verification


def require_chip_create_authority(
    governor_decision: dict[str, Any] | None,
    *,
    action_id: str | None = None,
) -> dict[str, Any]:
    verifier = _load_verify_governor_tool_authority()
    verification = verifier(
        governor_decision,
        tool_name=CHIP_CREATE_TOOL_NAME,
        owner_system=CHIP_CREATE_OWNER_SYSTEM,
        mutation_class=CHIP_CREATE_MUTATION_CLASS,
        action_id=action_id,
        require_pre_execution_ledger=True,
    )
    if not verification.get("allowed"):
        reasons = [str(item) for item in verification.get("reason_codes", []) if str(item).strip()]
        reason_text = ", ".join(reasons) if reasons else "governor_authority_denied"
        raise RuntimeError("Chip creation requires GovernorDecisionV1 chip-create authority: " + reason_text)
    return verification


def require_collective_publish_authority(
    governor_decision: dict[str, Any] | None,
    *,
    action_id: str | None = None,
) -> dict[str, Any]:
    verifier = _load_verify_governor_tool_authority()
    verification = verifier(
        governor_decision,
        tool_name=COLLECTIVE_PUBLISH_TOOL_NAME,
        owner_system=COLLECTIVE_PUBLISH_OWNER_SYSTEM,
        mutation_class=COLLECTIVE_PUBLISH_MUTATION_CLASS,
        action_id=action_id,
        require_pre_execution_ledger=True,
    )
    if not verification.get("allowed"):
        reasons = [str(item) for item in verification.get("reason_codes", []) if str(item).strip()]
        reason_text = ", ".join(reasons) if reasons else "governor_authority_denied"
        raise RuntimeError("Collective publish requires GovernorDecisionV1 collective-publish authority: " + reason_text)
    return verification


def require_collective_sync_authority(
    governor_decision: dict[str, Any] | None,
    *,
    action_id: str | None = None,
) -> dict[str, Any]:
    verifier = _load_verify_governor_tool_authority()
    verification = verifier(
        governor_decision,
        tool_name=COLLECTIVE_SYNC_TOOL_NAME,
        owner_system=COLLECTIVE_SYNC_OWNER_SYSTEM,
        mutation_class=COLLECTIVE_SYNC_MUTATION_CLASS,
        action_id=action_id,
        require_pre_execution_ledger=True,
    )
    if not verification.get("allowed"):
        reasons = [str(item) for item in verification.get("reason_codes", []) if str(item).strip()]
        reason_text = ", ".join(reasons) if reasons else "governor_authority_denied"
        raise RuntimeError("Collective sync requires GovernorDecisionV1 collective-sync authority: " + reason_text)
    return verification


def require_collective_absorb_authority(
    governor_decision: dict[str, Any] | None,
    *,
    action_id: str | None = None,
) -> dict[str, Any]:
    verifier = _load_verify_governor_tool_authority()
    verification = verifier(
        governor_decision,
        tool_name=COLLECTIVE_ABSORB_TOOL_NAME,
        owner_system=COLLECTIVE_ABSORB_OWNER_SYSTEM,
        mutation_class=COLLECTIVE_ABSORB_MUTATION_CLASS,
        action_id=action_id,
        require_pre_execution_ledger=True,
    )
    if not verification.get("allowed"):
        reasons = [str(item) for item in verification.get("reason_codes", []) if str(item).strip()]
        reason_text = ", ".join(reasons) if reasons else "governor_authority_denied"
        raise RuntimeError("Collective absorb requires GovernorDecisionV1 collective-absorb authority: " + reason_text)
    return verification


def _matching_action_args_path(
    governor_decision: dict[str, Any] | None,
    *,
    capability_id: str,
    action_type: str,
    args_path: str,
    action_id: str | None = None,
) -> bool:
    envelope = governor_decision.get("envelope") if isinstance(governor_decision, dict) else {}
    proposed_actions = envelope.get("proposed_actions") if isinstance(envelope, dict) else []
    if not isinstance(proposed_actions, list):
        return False
    for action in proposed_actions:
        if not isinstance(action, dict):
            continue
        if action.get("capability_id") != capability_id:
            continue
        if action.get("action_type") != action_type:
            continue
        if action_id is not None and str(action.get("action_id") or "") != action_id:
            continue
        args_ref = action.get("args_ref") if isinstance(action.get("args_ref"), dict) else {}
        if str(args_ref.get("path_or_uri") or "") == args_path:
            return True
    return False


def require_run_execution_authority(
    governor_decision: dict[str, Any] | None,
    *,
    args_path: str,
    action_id: str | None = None,
) -> dict[str, Any]:
    verifier = _load_verify_governor_tool_authority()
    verification = verifier(
        governor_decision,
        tool_name=RUN_EXECUTION_TOOL_NAME,
        owner_system=RUN_EXECUTION_OWNER_SYSTEM,
        mutation_class=RUN_EXECUTION_MUTATION_CLASS,
        action_id=action_id,
        require_pre_execution_ledger=True,
    )
    if verification.get("allowed") and not _matching_action_args_path(
        governor_decision,
        capability_id=RUN_EXECUTION_CAPABILITY_ID,
        action_type=RUN_EXECUTION_ACTION_TYPE,
        args_path=args_path,
        action_id=action_id,
    ):
        verification = {**verification, "allowed": False, "reason_codes": ["governor_action_args_path_mismatch"]}
    if not verification.get("allowed"):
        reasons = [str(item) for item in verification.get("reason_codes", []) if str(item).strip()]
        reason_text = ", ".join(reasons) if reasons else "governor_authority_denied"
        raise RuntimeError("Researcher run requires GovernorDecisionV1 run authority: " + reason_text)
    return verification

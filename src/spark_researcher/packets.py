from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

from .chips import load_chip_context
from .config import load_config
from .memory import sync_memory
from .paths import memory_root, resolve_runtime_root

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_NON_PACKET_KINDS = {"run", "outcome", "self_edit"}
_PREFERRED_KINDS = {
    "belief": 6,
    "startup_factor": 5,
    "trading_rule": 5,
    "content_belief": 5,
    "trading_failure": 4,
    "content_failure": 4,
}


@dataclass
class PacketRecord:
    packet_id: str
    kind: str
    domain: str
    title: str
    claim: str
    mechanism: str
    boundary: str
    confidence: float
    path: str
    score: int = 0


def _documents_root(runtime_root: Path) -> Path:
    return memory_root(runtime_root) / "documents"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _split_sections(text: str) -> dict[str, str]:
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip().lower()] = text[start:end].strip()
    return sections


def _first_line_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("# ").strip() or fallback
    return fallback


def _infer_kind(path: Path) -> str:
    stem = path.stem
    prefix = stem.split("-", 1)[0]
    return "self_edit" if prefix == "self" else prefix


def _infer_domain(kind: str, title: str, config_domain: str) -> str:
    lower_title = title.lower()
    if kind.startswith("startup") or "startup" in lower_title:
        return "startup"
    if kind.startswith("trading") or "trading" in lower_title:
        return "trading"
    if kind.startswith("content") or "content" in lower_title:
        return "content"
    return config_domain or "generic"


def _confidence(kind: str, score: int) -> float:
    base = 0.55 + min(score, 4) * 0.08
    if kind in {"startup_factor", "trading_rule", "content_belief"}:
        base += 0.08
    if kind in {"trading_failure", "content_failure"}:
        base += 0.04
    return round(min(base, 0.95), 2)


def _packet_from_path(path: Path, config_domain: str) -> PacketRecord | None:
    text = _read_text(path)
    title = _first_line_title(text, path.stem)
    kind = _infer_kind(path)
    if kind in _NON_PACKET_KINDS:
        return None
    sections = _split_sections(text)
    claim = (
        sections.get("claim")
        or sections.get("lesson")
        or sections.get("root lesson")
        or title
    )
    mechanism = sections.get("mechanism", "")
    boundary = (
        sections.get("failure boundary")
        or sections.get("transfer boundary")
        or sections.get("boundaries", "")
    )
    domain = _infer_domain(kind, title, config_domain)
    return PacketRecord(
        packet_id=path.stem,
        kind=kind,
        domain=domain,
        title=title,
        claim=claim.strip(),
        mechanism=mechanism.strip(),
        boundary=boundary.strip(),
        confidence=_confidence(kind, 0),
        path=str(path),
    )


def load_packets(config_path: Path, *, include_non_packets: bool = False) -> list[PacketRecord]:
    config = load_config(config_path)
    runtime_root = resolve_runtime_root(config_path)
    docs_root = _documents_root(runtime_root)
    chip_context = load_chip_context(config_path, config)
    config_domain = str(chip_context.manifest.get("domain", "generic")) if chip_context is not None else "generic"
    def collect() -> list[PacketRecord]:
        collected: list[PacketRecord] = []
        for path in sorted(docs_root.glob("*.md")):
            if path.name.upper() == "INDEX.MD":
                continue
            packet = _packet_from_path(path, config_domain)
            if packet is None and not include_non_packets:
                continue
            if packet is not None:
                collected.append(packet)
        return collected

    if not docs_root.exists() or not any(docs_root.glob("*.md")):
        sync_memory(config_path.parent.resolve(), runtime_root, goal=config.eval_goal, config_path=config_path)
    packets = collect()
    if not packets:
        sync_memory(config_path.parent.resolve(), runtime_root, goal=config.eval_goal, config_path=config_path)
        packets = collect()
    return packets


def search_packets(config_path: Path, query: str, *, limit: int = 5, domain: str | None = None) -> dict[str, Any]:
    terms = [term.lower() for term in query.split() if term.strip()]
    if not terms:
        raise RuntimeError("Packet query must not be empty.")
    selected: list[PacketRecord] = []
    for packet in load_packets(config_path):
        if domain and packet.domain not in {domain, "generic"}:
            continue
        haystack = " ".join((packet.title, packet.claim, packet.mechanism, packet.boundary)).lower()
        term_hits = sum(haystack.count(term) for term in terms)
        if term_hits <= 0:
            continue
        score = term_hits
        score += _PREFERRED_KINDS.get(packet.kind, 1)
        packet.score = score
        packet.confidence = _confidence(packet.kind, score)
        selected.append(packet)
    selected.sort(key=lambda item: (-item.score, item.packet_id))
    return {
        "query": query,
        "domain": domain,
        "packet_count": len(selected[:limit]),
        "packets": [asdict(item) for item in selected[:limit]],
    }


def packet_status(config_path: Path) -> dict[str, Any]:
    packets = load_packets(config_path)
    kind_counts: dict[str, int] = {}
    for packet in packets:
        kind_counts[packet.kind] = kind_counts.get(packet.kind, 0) + 1
    return {
        "packet_count": len(packets),
        "kinds": kind_counts,
        "packets_root": str(_documents_root(resolve_runtime_root(config_path))),
    }

"""Canonical exact cycle reconstruction and independently replayed evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evaluator import Transition, collatz_step, evaluate
from .experiment import _cycle_candidate_record, _persist_cycle_candidates
from .model import EvaluationResult


def _canonical_decimal(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal() and not (len(value) > 1 and value[0] == "0"):
        return int(value)
    raise ValueError("integer evidence must be a complete canonical positive decimal")


def reconstruct_cycle_members(
    start: int,
    first_seen_step: int,
    repeated_at_step: int,
    *,
    transition: Transition = collatz_step,
) -> list[int]:
    """Replay states through ``repeated_at_step`` and slice [first_seen:repeated_at)."""
    if start <= 0 or first_seen_step < 0 or repeated_at_step <= first_seen_step:
        raise ValueError("invalid cycle reconstruction bounds")
    states = [start]
    state = start
    for _ in range(repeated_at_step):
        state = transition(state)
        states.append(state)
    if states[first_seen_step] != states[repeated_at_step]:
        raise ValueError("replay bounds do not identify a repeated state")
    return states[first_seen_step:repeated_at_step]


def cycle_members_close(members: list[int], *, transition: Transition = collatz_step) -> bool:
    if not members:
        return False
    return all(transition(members[i]) == members[(i + 1) % len(members)] for i in range(len(members)))


def evidence_from_result(
    *,
    result: EvaluationResult,
    pilot_id: str | None = None,
    experiment_id: str | None = None,
    strategy: str,
    deterministic_seed: str,
    metadata: dict[str, Any] | None = None,
    transition: Transition = collatz_step,
) -> dict[str, Any]:
    if result.outcome != "repeated_state":
        raise ValueError("cycle evidence requires a repeated_state result")
    members = reconstruct_cycle_members(
        result.start, result.first_seen_step, result.repeated_at_step, transition=transition  # type: ignore[arg-type]
    )
    evidence: dict[str, Any] = {
        "starting_integer": str(result.start),
        "repeated_integer": result.repeated_integer,
        "first_seen_step": result.first_seen_step,
        "repeated_at_step": result.repeated_at_step,
        "cycle_length": result.cycle_length,
        "cycle_members": [str(member) for member in members],
        "strategy": strategy,
        "deterministic_seed": deterministic_seed,
        "validation_mode": (metadata or {}).get("validation_mode"),
        "independent_replay_confirmed": False,
    }
    if pilot_id is not None:
        evidence["pilot_id"] = pilot_id
    if experiment_id is not None:
        evidence["experiment_id"] = experiment_id
    if metadata:
        evidence.update(metadata)
    evidence["independent_replay_confirmed"] = verify_cycle_evidence(evidence, transition=transition)[0]
    return evidence


def verify_cycle_evidence(evidence: dict[str, Any], *, transition: Transition = collatz_step) -> tuple[bool, str]:
    try:
        start = _canonical_decimal(evidence.get("starting_integer"))
        repeated = _canonical_decimal(evidence.get("repeated_integer"))
        first_seen = evidence.get("first_seen_step")
        repeated_at = evidence.get("repeated_at_step")
        cycle_length = evidence.get("cycle_length")
        raw_members = evidence.get("cycle_members")
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (first_seen, repeated_at, cycle_length)):
            return False, "cycle scalar steps/length are not integers"
        if not isinstance(raw_members, list):
            return False, "cycle_members is not a list"
        members = [_canonical_decimal(v) for v in raw_members]
        replay = evaluate(start, transition=transition)
        if replay.outcome != "repeated_state":
            return False, "replay did not find a repeated state"
        checks = [
            (replay.repeated_state == repeated, "wrong repeated integer"),
            (replay.first_seen_step == first_seen, "wrong first_seen_step"),
            (replay.repeated_at_step == repeated_at, "wrong repeated_at_step"),
            (replay.cycle_length == cycle_length, "wrong cycle_length"),
        ]
        for ok, reason in checks:
            if not ok:
                return False, reason
        reconstructed = reconstruct_cycle_members(start, first_seen, repeated_at, transition=transition)
        if reconstructed != members:
            return False, "cycle members differ from independent reconstruction"
        if len(members) != cycle_length:
            return False, "cycle member count does not equal cycle length"
        if not cycle_members_close(members, transition=transition):
            return False, "cycle closure is broken"
        if members[0] != repeated:
            return False, "repeated integer is not first cycle member"
        if 1 in members:
            return False, "trivial cycle contains 1"
        return True, "confirmed"
    except (ValueError, TypeError) as error:
        return False, str(error)


def persist_nontrivial_discovery(output_root: Path, evidence: dict[str, Any]) -> None:
    if not evidence.get("independent_replay_confirmed"):
        raise ValueError("cannot persist unconfirmed discovery")
    path = output_root / "results" / "nontrivial_cycle_discovery.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    members = "\n".join(str(member) for member in evidence["cycle_members"])
    md = (
        "# Nontrivial Collatz Cycle Found\n\n"
        f"- Starting integer: `{evidence['starting_integer']}`\n"
        f"- Repeated integer: `{evidence['repeated_integer']}`\n"
        f"- Cycle length: {evidence['cycle_length']}\n"
        f"- Strategy: `{evidence['strategy']}`\n"
        f"- Identifier: `{evidence.get('pilot_id') or evidence.get('experiment_id')}`\n"
        f"- Independent replay confirmed: {evidence['independent_replay_confirmed']}\n\n"
        "## Exact ordered cycle\n\n```text\n" + members + "\n```\n"
    )
    (output_root / "NONTRIVIAL_CYCLE_FOUND.md").write_text(md)


def persist_compact_cycle_candidate(output_root: Path, result: EvaluationResult, identifier: str, strategy: str, metadata: dict[str, Any] | None = None) -> None:
    _persist_cycle_candidates(output_root, [_cycle_candidate_record(result=result, candidate=result.start, experiment_id=identifier, strategy=strategy, metadata=metadata)])

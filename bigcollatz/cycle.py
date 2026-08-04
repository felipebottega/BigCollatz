"""Canonical cycle reconstruction, verification, and discovery artifacts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .evaluator import Transition, collatz_step, evaluate
from .model import EvaluationResult


def is_canonical_decimal(value: str) -> bool:
    return isinstance(value, str) and value.isascii() and value.isdigit() and (value == "0" or not value.startswith("0"))


def reconstruct_cycle(start: int, result: EvaluationResult, *, transition: Transition = collatz_step) -> list[int]:
    """Replay ``start`` and return states[first_seen_step:repeated_at_step]."""
    if result.outcome != "repeated_state":
        raise ValueError("cycle reconstruction requires a repeated_state result")
    if result.first_seen_step is None or result.repeated_at_step is None or result.cycle_length is None:
        raise ValueError("repeated_state result lacks complete cycle indexes")
    states = [start]
    state = start
    for _ in range(result.repeated_at_step):
        state = transition(state)
        states.append(state)
    members = states[result.first_seen_step:result.repeated_at_step]
    if not members or members[0] != int(result.repeated_integer):
        raise ValueError("reconstructed first member does not match repeated_integer")
    if len(members) != result.cycle_length:
        raise ValueError("reconstructed cycle length mismatch")
    for left, right in zip(members, members[1:]):
        if transition(left) != right:
            raise ValueError("cycle transition mismatch")
    if transition(members[-1]) != members[0]:
        raise ValueError("cycle closure mismatch")
    return members


@dataclass(frozen=True)
class VerificationResult:
    confirmed: bool
    members: list[int]
    failure_reason: str | None = None


def verify_cycle_evidence(
    *, start: int, expected: EvaluationResult, supplied_cycle_members: list[str] | None = None,
    transition: Transition = collatz_step,
) -> VerificationResult:
    """Independently replay and verify all scalar and ordered-member cycle evidence."""
    try:
        replay = evaluate(start, transition=transition)
        scalars = ("outcome", "total_steps_executed", "maximum_integer", "repeated_integer",
                   "first_seen_step", "repeated_at_step", "cycle_length")
        for field in scalars:
            if getattr(replay, field) != getattr(expected, field):
                return VerificationResult(False, [], f"scalar mismatch: {field}")
        members = reconstruct_cycle(start, replay, transition=transition)
        member_strings = [str(member) for member in members]
        if supplied_cycle_members is not None:
            if any(not is_canonical_decimal(value) for value in supplied_cycle_members):
                return VerificationResult(False, members, "noncanonical decimal cycle member")
            if supplied_cycle_members != member_strings:
                return VerificationResult(False, members, "ordered cycle members mismatch")
        if replay.repeated_integer != member_strings[0]:
            return VerificationResult(False, members, "repeated integer is not first cycle member")
        if len(members) != replay.cycle_length:
            return VerificationResult(False, members, "cycle length mismatch")
        if 1 in members:
            return VerificationResult(False, members, "trivial cycle contains 1")
        if any(not is_canonical_decimal(value) for value in [str(start), str(replay.repeated_integer), *member_strings]):
            return VerificationResult(False, members, "noncanonical decimal evidence")
        return VerificationResult(True, members, None)
    except Exception as exc:  # verification reports failures rather than trusting callers
        return VerificationResult(False, [], str(exc))


def write_discovery_artifacts(output_root: Path, *, result: EvaluationResult, members: list[int], metadata: dict[str, Any]) -> dict[str, Path]:
    discovery = {
        "starting_integer": str(result.start), "repeated_integer": result.repeated_integer,
        "first_seen_step": result.first_seen_step, "repeated_at_step": result.repeated_at_step,
        "cycle_length": result.cycle_length, "cycle_members": [str(member) for member in members],
        "independent_replay_confirmed": True, **metadata,
    }
    json_path = output_root / "results" / "nontrivial_cycle_discovery.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(discovery, indent=2, sort_keys=True) + "\n")
    md_path = output_root / "NONTRIVIAL_CYCLE_FOUND.md"
    lines = ["# Nontrivial Collatz Cycle Found", "", "Independent replay confirmation: true", ""]
    for key, value in discovery.items():
        if key == "cycle_members":
            lines += ["## Exact ordered cycle members", "", *[str(v) for v in value], ""]
        else:
            lines.append(f"- **{key}**: `{value}`")
    md_path.write_text("\n".join(lines) + "\n")
    return {"discovery": json_path, "markdown": md_path}

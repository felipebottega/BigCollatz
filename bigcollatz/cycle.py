"""Canonical exact cycle reconstruction, verification, and discovery artifacts."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluator import collatz_step, evaluate
from .model import EvaluationResult

Transition = Callable[[int], int]


@dataclass(frozen=True, slots=True)
class CycleVerification:
    confirmed: bool
    members: list[int]
    failure_reason: str | None = None


def is_canonical_decimal(text: object) -> bool:
    return isinstance(text, str) and text.isascii() and text.isdigit() and text != "" and (text == "0" or not text.startswith("0"))


def reconstruct_cycle(start: int, result: EvaluationResult, *, transition: Transition = collatz_step) -> list[int]:
    if result.outcome != "repeated_state" or result.first_seen_step is None or result.repeated_at_step is None or result.cycle_length is None:
        raise ValueError("repeated-state result with complete indices is required")
    states = [start]
    state = start
    for _ in range(result.repeated_at_step):
        state = transition(state)
        states.append(state)
    members = states[result.first_seen_step:result.repeated_at_step]
    if not members or members[0] != int(result.repeated_integer):
        raise ValueError("cycle does not begin at repeated_integer")
    if len(members) != result.cycle_length or len(members) != result.repeated_at_step - result.first_seen_step:
        raise ValueError("cycle length metadata disagrees with reconstructed states")
    for left, right in zip(members, members[1:]):
        if transition(left) != right:
            raise ValueError("cycle transition is invalid")
    if transition(members[-1]) != members[0]:
        raise ValueError("cycle closure is invalid")
    return members


def verify_cycle(
    *, start: int, result: EvaluationResult, claimed_members: list[int] | list[str] | None = None,
    transition: Transition = collatz_step,
) -> CycleVerification:
    try:
        replay = evaluate(start, transition=transition, max_steps=result.repeated_at_step)
        scalars = ("outcome", "total_steps_executed", "maximum_integer", "repeated_integer", "first_seen_step", "repeated_at_step", "cycle_length")
        for field in scalars:
            if getattr(replay, field) != getattr(result, field):
                return CycleVerification(False, [], f"scalar mismatch: {field}")
        members = reconstruct_cycle(start, replay, transition=transition)
        if claimed_members is not None:
            converted = []
            for value in claimed_members:
                if isinstance(value, str):
                    if not is_canonical_decimal(value):
                        return CycleVerification(False, members, "noncanonical decimal string")
                    converted.append(int(value))
                else:
                    converted.append(value)
            if converted != members:
                return CycleVerification(False, members, "claimed members do not match canonical reconstruction")
        if any(member == 1 for member in members):
            return CycleVerification(False, members, "trivial cycle contains 1")
        if replay.repeated_integer != str(members[0]):
            return CycleVerification(False, members, "repeated_integer is not first member")
        for member in members:
            if not is_canonical_decimal(str(member)):
                return CycleVerification(False, members, "noncanonical decimal string")
        return CycleVerification(True, members, None)
    except Exception as exc:  # verification converts failures to evidence, not trust
        return CycleVerification(False, [], str(exc))


def discovery_payload(*, start: int, result: EvaluationResult, members: list[int], context: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "starting_integer": str(start),
        "repeated_integer": result.repeated_integer,
        "first_seen_step": result.first_seen_step,
        "repeated_at_step": result.repeated_at_step,
        "cycle_length": result.cycle_length,
        "cycle_members": [str(member) for member in members],
        "independent_replay_confirmed": True,
    }
    payload.update(context)
    return payload


def write_discovery_artifacts(output_root: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    json_path = output_root / "results" / "nontrivial_cycle_discovery.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    md_path = output_root / "NONTRIVIAL_CYCLE_FOUND.md"
    lines = [
        "# Nontrivial Collatz Cycle Found", "",
        f"- Starting integer: `{payload['starting_integer']}`",
        f"- Repeated integer: `{payload['repeated_integer']}`",
        f"- First-seen step: {payload['first_seen_step']}",
        f"- Repeated-at step: {payload['repeated_at_step']}",
        f"- Exact cycle length: {payload['cycle_length']}",
        f"- Strategy: `{payload.get('strategy')}`",
        f"- Pilot/experiment identifier: `{payload.get('pilot_id', payload.get('experiment_id'))}`",
        f"- Cell identifier: `{payload.get('cell_id')}`",
        f"- Family: `{payload.get('family')}`",
        f"- Deterministic seed: `{payload.get('deterministic_seed')}`",
        f"- Generation parameters: `{json.dumps(payload.get('generation_parameters'), sort_keys=True)}`",
        f"- Source metadata: `{json.dumps(payload.get('source_metadata'), sort_keys=True)}`",
        f"- Validation mode: `{payload.get('validation_mode')}`",
        "- Independent replay confirmation: true", "", "## Exact ordered cycle members", "",
    ]
    lines += [f"{i}. `{member}`" for i, member in enumerate(payload["cycle_members"], 1)]
    md_path.write_text("\n".join(lines) + "\n")
    return json_path, md_path

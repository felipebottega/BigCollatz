"""Canonical cycle reconstruction, verification, and discovery artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluator import Transition, collatz_step, evaluate
from .experiment import _cycle_candidate_record, _persist_cycle_candidates
from .model import EvaluationResult


@dataclass(frozen=True)
class CycleVerification:
    confirmed: bool
    members: list[int]
    failure_reason: str | None = None


def _canonical_decimal(value: int) -> str:
    return str(value)


def reconstruct_cycle(start: int, result: EvaluationResult, *, transition: Transition = collatz_step) -> list[int]:
    if result.outcome != "repeated_state":
        raise ValueError("cycle reconstruction requires repeated_state result")
    result.validate()
    assert result.first_seen_step is not None and result.repeated_at_step is not None
    assert result.cycle_length is not None and result.repeated_state is not None
    states = [start]
    state = start
    for _ in range(result.repeated_at_step):
        state = transition(state)
        states.append(state)
    members = states[result.first_seen_step:result.repeated_at_step]
    verify_cycle_members(members, result, transition=transition)
    return members


def verify_cycle_members(members: list[int], result: EvaluationResult, *, transition: Transition = collatz_step) -> None:
    if result.repeated_state is None or result.first_seen_step is None or result.repeated_at_step is None or result.cycle_length is None:
        raise ValueError("complete repeated-state metadata is required")
    if not members:
        raise ValueError("cycle members are required")
    if members[0] != result.repeated_state:
        raise ValueError("first cycle member does not equal repeated integer")
    if len(members) != result.repeated_at_step - result.first_seen_step:
        raise ValueError("cycle member count does not match repeated-at minus first-seen")
    if len(members) != result.cycle_length:
        raise ValueError("cycle member count does not match cycle length")
    if 1 in members:
        raise ValueError("nontrivial cycle evidence must not contain 1")
    for value in members:
        if str(value) != _canonical_decimal(value):
            raise ValueError("noncanonical decimal evidence")
    for left, right in zip(members, members[1:]):
        if transition(left) != right:
            raise ValueError("cycle members are not in transition order")
    if transition(members[-1]) != members[0]:
        raise ValueError("cycle does not close exactly")


def verify_nontrivial_cycle(start: int, claimed_result: EvaluationResult, claimed_members: list[Any] | None = None, *, transition: Transition = collatz_step, max_steps: int | None = None) -> CycleVerification:
    try:
        replay = evaluate(start, transition=transition, max_steps=max_steps)
        claimed_result.validate()
        fields = ("outcome", "total_steps_executed", "maximum_integer", "repeated_state", "cycle_entry_step", "cycle_period", "repeated_integer", "first_seen_step", "repeated_at_step", "cycle_length")
        for field in fields:
            if getattr(replay, field) != getattr(claimed_result, field):
                return CycleVerification(False, [], f"{field} mismatch")
        if replay.outcome != "repeated_state":
            return CycleVerification(False, [], "independent replay did not find a repeated state")
        members = reconstruct_cycle(start, replay, transition=transition)
        if claimed_members is not None:
            canonical_claim = []
            for item in claimed_members:
                if not isinstance(item, str) or str(int(item)) != item:
                    return CycleVerification(False, members, "noncanonical decimal evidence")
                canonical_claim.append(int(item))
            if canonical_claim != members:
                return CycleVerification(False, members, "claimed cycle members mismatch")
        verify_cycle_members(members, replay, transition=transition)
        return CycleVerification(True, members, None)
    except Exception as exc:  # verifier returns concrete failure instead of propagating
        return CycleVerification(False, [], str(exc))


def write_discovery_artifacts(output_root: Path, *, starting_integer: int, result: EvaluationResult, cycle_members: list[int], pilot_id: str, strategy: str, deterministic_seed: str, cell_id: str, family: str, generation_parameters: dict[str, Any], source_metadata: dict[str, Any], validation_mode: str) -> dict[str, str]:
    verification = verify_nontrivial_cycle(starting_integer, result, [str(v) for v in cycle_members])
    if not verification.confirmed:
        raise ValueError(f"cycle verification failed: {verification.failure_reason}")
    compact = _cycle_candidate_record(result=result, candidate=starting_integer, experiment_id=pilot_id, strategy=strategy, metadata={"pilot_id": pilot_id, "cell_id": cell_id, "family": family})
    _persist_cycle_candidates(output_root, [compact])
    payload = {
        "starting_integer": str(starting_integer), "repeated_integer": result.repeated_integer,
        "first_seen_step": result.first_seen_step, "repeated_at_step": result.repeated_at_step,
        "cycle_length": result.cycle_length, "cycle_members": [str(v) for v in verification.members],
        "pilot_id": pilot_id, "strategy": strategy, "deterministic_seed": deterministic_seed,
        "cell_id": cell_id, "family": family, "generation_parameters": generation_parameters,
        "source_metadata": source_metadata, "validation_mode": validation_mode,
        "independent_replay_confirmed": True,
    }
    json_path = output_root / "results" / "nontrivial_cycle_discovery.json"
    md_path = output_root / "NONTRIVIAL_CYCLE_FOUND.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    md_path.write_text("\n".join(["# Nontrivial Cycle Found", "", f"Starting integer: `{starting_integer}`", f"Repeated integer: `{result.repeated_integer}`", f"First seen step: {result.first_seen_step}", f"Repeated at step: {result.repeated_at_step}", f"Cycle length: {result.cycle_length}", f"Pilot: `{pilot_id}`", f"Strategy: `{strategy}`", f"Deterministic seed: `{deterministic_seed}`", f"Cell: `{cell_id}`", f"Family: `{family}`", f"Generation parameters: `{json.dumps(generation_parameters, sort_keys=True)}`", f"Source metadata: `{json.dumps(source_metadata, sort_keys=True)}`", f"Validation mode: `{validation_mode}`", "Independent replay confirmed: true", "", "## Ordered cycle members", "", *[f"- `{v}`" for v in payload["cycle_members"]], ""]))
    return {"cycle_candidates": "results/cycle_candidates.json", "discovery_json": "results/nontrivial_cycle_discovery.json", "discovery_markdown": "NONTRIVIAL_CYCLE_FOUND.md"}

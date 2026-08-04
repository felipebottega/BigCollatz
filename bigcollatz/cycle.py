"""Canonical cycle reconstruction and independent verification."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from .evaluator import collatz_step, evaluate
from .model import EvaluationResult
Transition = Callable[[int], int]

@dataclass(frozen=True)
class CycleVerification:
    confirmed: bool
    cycle_members: list[int]
    failure: str | None = None

def reconstruct_cycle(start:int,result:EvaluationResult,*,transition:Transition=collatz_step)->list[int]:
    if result.outcome!="repeated_state": raise ValueError("repeated_state result required")
    if result.first_seen_step is None or result.repeated_at_step is None or result.cycle_length is None: raise ValueError("cycle metadata incomplete")
    states=[start]; state=start
    for _ in range(result.repeated_at_step):
        state=transition(state); states.append(state)
    members=states[result.first_seen_step:result.repeated_at_step]
    if len(members)!=result.cycle_length: raise ValueError("cycle length mismatch")
    if not members or members[0]!=int(result.repeated_integer): raise ValueError("repeated integer is not first member")
    return members

def verify_cycle_independently(start:int, evidence:EvaluationResult, claimed_members:list[int]|None=None,*,transition:Transition=collatz_step)->CycleVerification:
    try:
        replay=evaluate(start, transition=transition)
        members=reconstruct_cycle(start,replay,transition=transition)
        checks=[
            (replay.outcome=="repeated_state","replay did not repeat"),
            (replay.repeated_integer==evidence.repeated_integer,"repeated integer mismatch"),
            (replay.first_seen_step==evidence.first_seen_step,"first_seen_step mismatch"),
            (replay.repeated_at_step==evidence.repeated_at_step,"repeated_at_step mismatch"),
            (replay.cycle_length==evidence.cycle_length,"cycle_length mismatch"),
            (len(members)==replay.cycle_length,"member count mismatch"),
            (members[0]==int(replay.repeated_integer),"first member mismatch"),
            (1 not in members,"cycle contains 1"),
            (all(str(x)==format(x,'d') for x in members),"noncanonical decimal"),
        ]
        if claimed_members is not None:
            checks.append((members==claimed_members,"claimed members mismatch"))
        for ok,msg in checks:
            if not ok: return CycleVerification(False,members,msg)
        for a,b in zip(members,members[1:]):
            if transition(a)!=b: return CycleVerification(False,members,"broken transition")
        if transition(members[-1])!=members[0]: return CycleVerification(False,members,"broken closure")
        return CycleVerification(True,members)
    except Exception as e:
        return CycleVerification(False,[],str(e))

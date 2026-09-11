"""Exact large-integer Collatz experiments."""

from .evaluator import evaluate, evaluate_hashset
from .generator import baseline_candidates
from .model import EvaluationResult
from .cycle_equation import compose_cycle_equation, solve_cycle_equation
from .cycle_search import CycleSearchConfig, search_cycles
from .odd_map import odd_step

__all__ = [
    "CycleSearchConfig",
    "EvaluationResult",
    "baseline_candidates",
    "compose_cycle_equation",
    "evaluate",
    "evaluate_hashset",
    "odd_step",
    "search_cycles",
    "solve_cycle_equation",
]
__version__ = "0.1.0"

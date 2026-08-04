"""Exact large-integer Collatz experiments."""

from .evaluator import evaluate, evaluate_hashset
from .generator import baseline_candidates
from .model import EvaluationResult

__all__ = ["EvaluationResult", "baseline_candidates", "evaluate", "evaluate_hashset"]
__version__ = "0.1.0"


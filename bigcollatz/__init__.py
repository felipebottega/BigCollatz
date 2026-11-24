"""Exact algebraic search for Collatz cycles."""

from .cycle_equation import compose_cycle_equation, solve_cycle_equation
from .cycle_search import CycleSearchConfig, search_cycles
from .odd_map import odd_step

__all__ = [
    "CycleSearchConfig",
    "compose_cycle_equation",
    "odd_step",
    "search_cycles",
    "solve_cycle_equation",
]
__version__ = "0.1.0"

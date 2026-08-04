"""Typed evaluator result and schema-v1 validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Outcome = Literal["reached_one", "repeated_state", "interrupted"]
SUPPORTED_OUTCOMES = frozenset(("reached_one", "repeated_state", "interrupted"))
SUPPORTED_STOPPING_REASONS = frozenset(
    ("reached_one", "repeated_state", "user_stop", "process_shutdown",
     "resource_exhaustion", "safety_limit", "error")
)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _decimal(value: object, field: str) -> int:
    if not isinstance(value, str) or not value or not value.isascii():
        raise ValueError(f"{field} must be a canonical decimal string")
    unsigned = value[1:] if value.startswith("-") else value
    if (not unsigned.isdigit() or unsigned == "" or
            (len(unsigned) > 1 and unsigned.startswith("0")) or value == "-0"):
        raise ValueError(f"{field} must be a canonical decimal string")
    return int(value)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    start: int
    total_steps_executed: int
    outcome: Outcome
    maximum_integer: int
    repeated_state: int | None = None
    cycle_entry_step: int | None = None
    cycle_period: int | None = None
    stopping_reason: str = "reached_one"
    safety_limit_kind: str | None = None
    safety_limit_value: int | None = None
    repeated_integer: str | None = None
    first_seen_step: int | None = None
    repeated_at_step: int | None = None
    cycle_length: int | None = None


    def __post_init__(self) -> None:
        if self.outcome == "repeated_state" and self.repeated_state is not None:
            if self.repeated_integer is None:
                object.__setattr__(self, "repeated_integer", str(self.repeated_state))
            if self.first_seen_step is None and self.cycle_entry_step is not None:
                object.__setattr__(self, "first_seen_step", self.cycle_entry_step)
            if self.cycle_period is not None and self.cycle_entry_step is not None:
                if self.repeated_at_step is None:
                    object.__setattr__(self, "repeated_at_step", self.cycle_entry_step + self.cycle_period)
                if self.cycle_length is None:
                    object.__setattr__(self, "cycle_length", self.cycle_period)

    @property
    def reached_one(self) -> bool:
        return self.outcome == "reached_one"

    @property
    def repeated_state_found(self) -> bool:
        return self.outcome == "repeated_state"

    @property
    def censored(self) -> bool:
        return self.outcome == "interrupted"

    def validate(self) -> None:
        integer_fields = (self.start, self.total_steps_executed, self.maximum_integer)
        if not all(_is_int(value) for value in integer_fields):
            raise ValueError("integer metrics must have integer types")
        if not isinstance(self.outcome, str) or self.outcome not in SUPPORTED_OUTCOMES:
            raise ValueError("unsupported outcome")
        if not isinstance(self.stopping_reason, str) or self.stopping_reason not in SUPPORTED_STOPPING_REASONS:
            raise ValueError("unsupported stopping reason")
        if self.start <= 0 or self.total_steps_executed < 0 or self.maximum_integer < self.start:
            raise ValueError("invalid positive integer or metric")
        details = (self.repeated_state, self.cycle_entry_step, self.cycle_period,
                   self.repeated_integer, self.first_seen_step, self.repeated_at_step,
                   self.cycle_length)
        if self.repeated_state_found:
            if (any(value is None for value in details) or
                    not all(_is_int(value) for value in (self.repeated_state, self.cycle_entry_step, self.cycle_period, self.first_seen_step, self.repeated_at_step, self.cycle_length)) or
                    not isinstance(self.repeated_integer, str) or
                    self.cycle_entry_step < 0 or self.cycle_period < 1 or  # type: ignore[operator]
                    self.cycle_entry_step + self.cycle_period != self.total_steps_executed or  # type: ignore[operator]
                    self.repeated_integer != str(self.repeated_state) or
                    self.first_seen_step != self.cycle_entry_step or
                    self.repeated_at_step != self.total_steps_executed or
                    self.cycle_length != self.cycle_period):
                raise ValueError("repetition requires complete cycle details")
        elif any(value is not None for value in details):
            raise ValueError("cycle details are exclusive to repeated_state")
        expected_reason = self.outcome if self.outcome != "interrupted" else None
        if expected_reason is not None and self.stopping_reason != expected_reason:
            raise ValueError("outcome and stopping reason disagree")
        if self.outcome == "interrupted" and self.stopping_reason in {"reached_one", "repeated_state"}:
            raise ValueError("interrupted results require an operational stopping reason")
        if self.stopping_reason == "safety_limit":
            if (not isinstance(self.safety_limit_kind, str) or not self.safety_limit_kind or
                    not _is_int(self.safety_limit_value) or self.safety_limit_value < 0):
                raise ValueError("safety limit provenance is required")
        elif self.safety_limit_kind is not None or self.safety_limit_value is not None:
            raise ValueError("limit provenance is exclusive to safety_limit")

    def to_record(self, **metadata: Any) -> dict[str, Any]:
        self.validate()
        data = asdict(self)
        data.update(
            schema_version=1,
            start=str(self.start),
            decimal_digits=len(str(self.start)),
            maximum_integer=str(self.maximum_integer),
            maximum_bit_length=self.maximum_integer.bit_length(),
            reached_one=self.reached_one,
            repeated_state_found=self.repeated_state_found,
            repeated_state=None if self.repeated_state is None else str(self.repeated_state),
            censored=self.censored,
        )
        data.update(metadata)
        return data

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "EvaluationResult":
        if not isinstance(record, dict):
            raise ValueError("record must be an object")
        required = ("schema_version", "start", "decimal_digits", "total_steps_executed",
                    "outcome", "maximum_integer", "maximum_bit_length", "stopping_reason",
                    "reached_one", "repeated_state_found", "censored")
        if any(field not in record for field in required):
            raise ValueError("record is missing required fields")
        if not _is_int(record["schema_version"]) or record["schema_version"] != 1:
            raise ValueError("unsupported schema version")
        start = _decimal(record["start"], "start")
        maximum = _decimal(record["maximum_integer"], "maximum_integer")
        repeated = None if record.get("repeated_state") is None else _decimal(record["repeated_state"], "repeated_state")
        result = cls(
            start=start, total_steps_executed=record["total_steps_executed"],
            outcome=record["outcome"], maximum_integer=maximum,
            repeated_state=repeated,
            cycle_entry_step=record.get("cycle_entry_step"), cycle_period=record.get("cycle_period"),
            stopping_reason=record["stopping_reason"], safety_limit_kind=record.get("safety_limit_kind"),
            safety_limit_value=record.get("safety_limit_value"),
            repeated_integer=record.get("repeated_integer"),
            first_seen_step=record.get("first_seen_step"),
            repeated_at_step=record.get("repeated_at_step"),
            cycle_length=record.get("cycle_length"),
        )
        result.validate()
        if not _is_int(record["decimal_digits"]) or record["decimal_digits"] != len(str(result.start)):
            raise ValueError("incorrect decimal digit count")
        if not _is_int(record["maximum_bit_length"]) or record["maximum_bit_length"] != result.maximum_integer.bit_length():
            raise ValueError("incorrect maximum bit length")
        flags = (record["reached_one"], record["repeated_state_found"], record["censored"])
        if not all(isinstance(value, bool) for value in flags):
            raise ValueError("derived flags must be booleans")
        if flags != (result.reached_one, result.repeated_state_found, result.censored):
            raise ValueError("inconsistent derived flags")
        return result

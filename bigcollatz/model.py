"""Typed evaluator result and schema-v1 validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Outcome = Literal["reached_one", "repeated_state", "interrupted"]


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
        if self.start <= 0 or self.total_steps_executed < 0 or self.maximum_integer < self.start:
            raise ValueError("invalid positive integer or metric")
        details = (self.repeated_state, self.cycle_entry_step, self.cycle_period)
        if self.repeated_state_found:
            if any(value is None for value in details) or self.cycle_period < 1:  # type: ignore[operator]
                raise ValueError("repetition requires complete cycle details")
        elif any(value is not None for value in details):
            raise ValueError("cycle details are exclusive to repeated_state")
        if self.censored != (self.stopping_reason not in {"reached_one", "repeated_state"}):
            raise ValueError("operational stops must be censored")
        if self.stopping_reason == "safety_limit":
            if self.safety_limit_kind is None or self.safety_limit_value is None:
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
        for field in ("start", "maximum_integer"):
            text = record[field]
            if not isinstance(text, str) or not text.isdigit() or (len(text) > 1 and text[0] == "0"):
                raise ValueError(f"{field} must be a canonical decimal string")
        result = cls(
            start=int(record["start"]), total_steps_executed=record["total_steps_executed"],
            outcome=record["outcome"], maximum_integer=int(record["maximum_integer"]),
            repeated_state=None if record.get("repeated_state") is None else int(record["repeated_state"]),
            cycle_entry_step=record.get("cycle_entry_step"), cycle_period=record.get("cycle_period"),
            stopping_reason=record["stopping_reason"], safety_limit_kind=record.get("safety_limit_kind"),
            safety_limit_value=record.get("safety_limit_value"),
        )
        result.validate()
        if record.get("decimal_digits") != len(str(result.start)):
            raise ValueError("incorrect decimal digit count")
        if record.get("reached_one") != result.reached_one or record.get("censored") != result.censored:
            raise ValueError("inconsistent derived flags")
        return result

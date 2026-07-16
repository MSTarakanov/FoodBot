from __future__ import annotations

from office_food_bot.result import Failure, Result, Success, failure, success


def test_map_transforms_only_success_value() -> None:
    success_result: Result[int, str] = success(2)
    failure_result: Result[int, str] = failure("invalid")

    assert success_result.map(lambda value: value * 3) == Success[int, str](6)
    assert failure_result.map(lambda value: value * 3) == Failure[int, str]("invalid")


def test_map_error_transforms_only_failure_value() -> None:
    success_result: Result[int, str] = success(2)
    failure_result: Result[int, str] = failure("invalid")

    assert success_result.map_error(str.upper) == Success[int, str](2)
    assert failure_result.map_error(str.upper) == Failure[int, str]("INVALID")


def test_and_then_runs_next_step_after_success() -> None:
    result: Result[int, str] = success(2)

    assert result.and_then(lambda value: success(value + 1)) == Success[int, str](3)


def test_and_then_keeps_failure_without_running_next_step() -> None:
    events: list[str] = []
    result: Result[int, str] = failure("invalid")

    def next_step(value: int) -> Result[int, str]:
        events.append(str(value))
        return success(value + 1)

    assert result.and_then(next_step) == Failure[int, str]("invalid")
    assert events == []

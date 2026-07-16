from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass


class Result[ValueT, ErrorT](ABC):
    @abstractmethod
    def fold[OutputT](
        self,
        on_success: Callable[[ValueT], OutputT],
        on_error: Callable[[ErrorT], OutputT],
    ) -> OutputT: ...

    def map[MappedValueT](
        self,
        transform: Callable[[ValueT], MappedValueT],
    ) -> Result[MappedValueT, ErrorT]:
        return self.fold(
            lambda value: Success[MappedValueT, ErrorT](transform(value)),
            lambda error: Failure[MappedValueT, ErrorT](error),
        )

    def map_error[MappedErrorT](
        self,
        transform: Callable[[ErrorT], MappedErrorT],
    ) -> Result[ValueT, MappedErrorT]:
        return self.fold(
            lambda value: Success[ValueT, MappedErrorT](value),
            lambda error: Failure[ValueT, MappedErrorT](transform(error)),
        )

    def and_then[NextValueT](
        self,
        transform: Callable[[ValueT], Result[NextValueT, ErrorT]],
    ) -> Result[NextValueT, ErrorT]:
        return self.fold(
            transform,
            lambda error: Failure[NextValueT, ErrorT](error),
        )


@dataclass(frozen=True, slots=True)
class Success[ValueT, ErrorT](Result[ValueT, ErrorT]):
    value: ValueT

    def fold[OutputT](
        self,
        on_success: Callable[[ValueT], OutputT],
        on_error: Callable[[ErrorT], OutputT],
    ) -> OutputT:
        del on_error
        return on_success(self.value)


@dataclass(frozen=True, slots=True)
class Failure[ValueT, ErrorT](Result[ValueT, ErrorT]):
    error: ErrorT

    def fold[OutputT](
        self,
        on_success: Callable[[ValueT], OutputT],
        on_error: Callable[[ErrorT], OutputT],
    ) -> OutputT:
        del on_success
        return on_error(self.error)


def success[ValueT, ErrorT](value: ValueT) -> Result[ValueT, ErrorT]:
    return Success[ValueT, ErrorT](value)


def failure[ValueT, ErrorT](error: ErrorT) -> Result[ValueT, ErrorT]:
    return Failure[ValueT, ErrorT](error)

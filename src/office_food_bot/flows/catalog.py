from __future__ import annotations

from office_food_bot.flows.contracts import ActiveFlow


class FlowCatalog:
    def __init__(self, flows: tuple[ActiveFlow, ...]) -> None:
        names = tuple(flow.name for flow in flows)
        if not names:
            raise ValueError("At least one flow is required")
        if len(names) != len(set(names)):
            raise ValueError("Flow names must be unique")
        self._flows = flows
        self._by_name = {flow.name: flow for flow in flows}

    @property
    def flows(self) -> tuple[ActiveFlow, ...]:
        return self._flows

    def resolve(self, name: str) -> ActiveFlow | None:
        return self._by_name.get(name)

from __future__ import annotations

from office_food_bot.flows.contracts import ActiveFlow, FlowId


class FlowCatalog:
    def __init__(self, flows: tuple[ActiveFlow, ...]) -> None:
        flow_ids = tuple(flow.flow_id for flow in flows)
        if not flow_ids:
            raise ValueError("At least one flow is required")
        if len(flow_ids) != len(set(flow_ids)):
            raise ValueError("Flow ids must be unique")
        self._flows = flows
        self._by_id = {flow.flow_id: flow for flow in flows}

    @property
    def flows(self) -> tuple[ActiveFlow, ...]:
        return self._flows

    def resolve(self, flow_id: FlowId) -> ActiveFlow | None:
        return self._by_id.get(flow_id)

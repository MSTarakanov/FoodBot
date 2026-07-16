from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from office_food_bot.integrations.splitwise import (
    HttpSplitwiseClient,
    SplitwiseGroupKind,
    SplitwiseLookupKind,
    SplitwiseService,
    SplitwiseUnavailableError,
)
from office_food_bot.models import SplitwiseBalance, SplitwiseMember


class FakeSplitwiseClient:
    def __init__(
        self,
        members: tuple[SplitwiseMember, ...],
        *,
        unavailable: bool = False,
    ) -> None:
        self._members = members
        self._unavailable = unavailable
        self.requested_group_ids: list[int] = []

    async def group_members(self, group_id: int) -> tuple[SplitwiseMember, ...]:
        self.requested_group_ids.append(group_id)
        if self._unavailable:
            raise SplitwiseUnavailableError("Splitwise is unavailable")
        return self._members


async def test_splitwise_service_finds_email_case_insensitively() -> None:
    member = SplitwiseMember(
        splitwise_user_id=1001,
        first_name="Max",
        last_name=None,
        email="Max@Example.com",
    )
    client = FakeSplitwiseClient((member,))

    result = await SplitwiseService(client, 55).find_member_by_email(" max@example.COM ")

    assert result.kind == SplitwiseLookupKind.FOUND
    assert result.member == member
    assert client.requested_group_ids == [55]


async def test_splitwise_service_returns_not_found_for_missing_email() -> None:
    client = FakeSplitwiseClient(
        (
            SplitwiseMember(
                splitwise_user_id=1001,
                first_name="Max",
                last_name=None,
                email="max@example.com",
            ),
        )
    )

    result = await SplitwiseService(client, 55).find_member_by_email("olya@example.com")

    assert result.kind == SplitwiseLookupKind.NOT_FOUND
    assert result.member is None


async def test_splitwise_service_returns_unavailable_when_client_fails() -> None:
    client = FakeSplitwiseClient((), unavailable=True)

    result = await SplitwiseService(client, 55).find_member_by_email("max@example.com")

    assert result.kind == SplitwiseLookupKind.UNAVAILABLE
    assert result.member is None


async def test_splitwise_service_returns_unavailable_without_config() -> None:
    result = await SplitwiseService(None, None).find_member_by_email("max@example.com")

    assert result.kind == SplitwiseLookupKind.UNAVAILABLE
    assert result.member is None


async def test_http_splitwise_client_sends_auth_and_user_agent_headers() -> None:
    captured_requests: list[httpx.Request] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            request=request,
            json={
                "group": {
                    "members": [
                        {
                            "id": 1001,
                            "first_name": "Max",
                            "last_name": None,
                            "email": "max@example.com",
                            "balance": [
                                {
                                    "currency_code": "RSD",
                                    "amount": "-5.02",
                                }
                            ],
                        }
                    ]
                }
            },
        )

    client = HttpSplitwiseClient(
        "test-key",
        base_url="https://splitwise.test",
        transport=httpx.MockTransport(handle_request),
    )

    members = await client.group_members(55)

    assert len(captured_requests) == 1
    assert captured_requests[0].headers["authorization"] == "Bearer test-key"
    assert captured_requests[0].headers["user-agent"] == "OfficeFoodBot/0.1"
    assert captured_requests[0].url == "https://splitwise.test/get_group/55"
    assert members == (
        SplitwiseMember(
            splitwise_user_id=1001,
            first_name="Max",
            last_name=None,
            email="max@example.com",
            balance=(
                SplitwiseBalance(
                    currency_code="RSD",
                    amount=Decimal("-5.02"),
                ),
            ),
        ),
    )


@pytest.mark.parametrize("balance_payload", [[], None])
async def test_http_splitwise_client_treats_empty_or_missing_balance_as_empty(
    balance_payload: object,
) -> None:
    def member_payload() -> dict[str, object]:
        payload: dict[str, object] = {
            "id": 1001,
            "first_name": "Max",
            "last_name": None,
            "email": "max@example.com",
        }
        if balance_payload is not None:
            payload["balance"] = balance_payload
        return payload

    client = HttpSplitwiseClient(
        "test-key",
        base_url="https://splitwise.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                request=request,
                json={"group": {"members": [member_payload()]}},
            )
        ),
    )

    assert await client.group_members(55) == (
        SplitwiseMember(
            splitwise_user_id=1001,
            first_name="Max",
            last_name=None,
            email="max@example.com",
        ),
    )


async def test_splitwise_service_returns_group_members() -> None:
    member = SplitwiseMember(
        splitwise_user_id=1001,
        first_name="Max",
        last_name=None,
        email="max@example.com",
    )
    client = FakeSplitwiseClient((member,))

    result = await SplitwiseService(client, 55).group_members()

    assert result.kind == SplitwiseGroupKind.AVAILABLE
    assert result.members == (member,)
    assert client.requested_group_ids == [55]


async def test_splitwise_service_returns_unavailable_group_without_config() -> None:
    result = await SplitwiseService(None, None).group_members()

    assert result.kind == SplitwiseGroupKind.UNAVAILABLE
    assert result.members == ()


@pytest.mark.parametrize("status_code", [401, 403, 404])
async def test_splitwise_service_returns_unavailable_for_http_auth_or_group_errors(
    status_code: int,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status_code, request=request)
    )
    client = HttpSplitwiseClient(
        "test-key",
        base_url="https://splitwise.test",
        transport=transport,
    )

    result = await SplitwiseService(client, 55).find_member_by_email("max@example.com")

    assert result.kind == SplitwiseLookupKind.UNAVAILABLE
    assert result.member is None


async def test_splitwise_service_returns_unavailable_for_invalid_balance_amount() -> None:
    client = HttpSplitwiseClient(
        "test-key",
        base_url="https://splitwise.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                request=request,
                json={
                    "group": {
                        "members": [
                            {
                                "id": 1001,
                                "first_name": "Max",
                                "last_name": None,
                                "email": "max@example.com",
                                "balance": [
                                    {
                                        "currency_code": "RSD",
                                        "amount": "not-money",
                                    }
                                ],
                            }
                        ]
                    }
                },
            )
        ),
    )

    result = await SplitwiseService(client, 55).find_member_by_email("max@example.com")

    assert result.kind == SplitwiseLookupKind.UNAVAILABLE
    assert result.member is None


async def test_splitwise_service_returns_unavailable_for_network_errors() -> None:
    def raise_network_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network failed", request=request)

    client = HttpSplitwiseClient(
        "test-key",
        base_url="https://splitwise.test",
        transport=httpx.MockTransport(raise_network_error),
    )

    result = await SplitwiseService(client, 55).find_member_by_email("max@example.com")

    assert result.kind == SplitwiseLookupKind.UNAVAILABLE
    assert result.member is None

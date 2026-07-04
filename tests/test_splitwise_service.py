from __future__ import annotations

import httpx
import pytest

from office_food_bot.models import SplitwiseMember
from office_food_bot.services.splitwise import (
    HttpSplitwiseClient,
    SplitwiseLookupKind,
    SplitwiseService,
    SplitwiseUnavailableError,
)


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

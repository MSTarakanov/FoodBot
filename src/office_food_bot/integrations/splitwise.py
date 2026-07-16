from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Protocol, assert_never

import httpx

from office_food_bot.application.splitwise.models import SplitwiseBalance, SplitwiseMember

SPLITWISE_API_BASE_URL = "https://secure.splitwise.com/api/v3.0"
SPLITWISE_USER_AGENT = "OfficeFoodBot/0.1"


class SplitwiseLookupKind(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"


class SplitwiseGroupKind(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SplitwiseLookupResult:
    kind: SplitwiseLookupKind
    member: SplitwiseMember | None = None


@dataclass(frozen=True)
class SplitwiseGroupResult:
    kind: SplitwiseGroupKind
    members: tuple[SplitwiseMember, ...] = ()


class SplitwiseUnavailableError(RuntimeError):
    pass


class SplitwiseGroupClient(Protocol):
    async def group_members(self, group_id: int) -> tuple[SplitwiseMember, ...]: ...


class HttpSplitwiseClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = SPLITWISE_API_BASE_URL,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def group_members(self, group_id: int) -> tuple[SplitwiseMember, ...]:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    f"{self._base_url}/get_group/{group_id}",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "User-Agent": SPLITWISE_USER_AGENT,
                    },
                )
            if response.status_code in {401, 403, 404}:
                raise SplitwiseUnavailableError("Splitwise group is unavailable")
            response.raise_for_status()
            return _members_from_group_payload(response.json())
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            msg = "Splitwise API request failed"
            raise SplitwiseUnavailableError(msg) from error


class SplitwiseService:
    def __init__(
        self,
        client: SplitwiseGroupClient | None,
        group_id: int | None,
    ) -> None:
        self._client = client
        self._group_id = group_id

    async def find_member_by_email(self, raw_email: str) -> SplitwiseLookupResult:
        email = normalize_email(raw_email)
        if not email:
            return SplitwiseLookupResult(SplitwiseLookupKind.UNAVAILABLE)

        result = await self.group_members()
        match result.kind:
            case SplitwiseGroupKind.UNAVAILABLE:
                return SplitwiseLookupResult(SplitwiseLookupKind.UNAVAILABLE)
            case SplitwiseGroupKind.AVAILABLE:
                pass
            case _:
                assert_never(result.kind)

        for member in result.members:
            if normalize_email(member.email) == email:
                return SplitwiseLookupResult(SplitwiseLookupKind.FOUND, member)

        return SplitwiseLookupResult(SplitwiseLookupKind.NOT_FOUND)

    async def group_members(self) -> SplitwiseGroupResult:
        if self._client is None or self._group_id is None:
            return SplitwiseGroupResult(SplitwiseGroupKind.UNAVAILABLE)

        try:
            members = await self._client.group_members(self._group_id)
        except SplitwiseUnavailableError:
            return SplitwiseGroupResult(SplitwiseGroupKind.UNAVAILABLE)

        return SplitwiseGroupResult(SplitwiseGroupKind.AVAILABLE, members)


def normalize_email(raw_email: str) -> str:
    return raw_email.strip().lower()


def _members_from_group_payload[Payload](payload: Payload) -> tuple[SplitwiseMember, ...]:
    match payload:
        case dict() as group_payload:
            group = group_payload["group"]
        case _:
            msg = "Splitwise group payload must be an object"
            raise ValueError(msg)

    match group:
        case dict() as group_data:
            members = group_data["members"]
        case _:
            msg = "Splitwise group must be an object"
            raise ValueError(msg)

    match members:
        case list() as member_payloads:
            return tuple(_member_from_payload(member) for member in member_payloads)
        case _:
            msg = "Splitwise group members must be a list"
            raise ValueError(msg)


def _member_from_payload[Payload](payload: Payload) -> SplitwiseMember:
    match payload:
        case dict() as member:
            return SplitwiseMember(
                splitwise_user_id=int(member["id"]),
                first_name=str(member.get("first_name") or ""),
                last_name=_optional_str(member.get("last_name")),
                email=str(member["email"]),
                balance=_balances_from_payload(member.get("balance", [])),
            )
        case _:
            msg = "Splitwise member must be an object"
            raise ValueError(msg)


def _balances_from_payload[Payload](payload: Payload) -> tuple[SplitwiseBalance, ...]:
    if payload is None:
        return ()
    match payload:
        case list() as balances:
            return tuple(_balance_from_payload(balance) for balance in balances)
        case _:
            msg = "Splitwise member balance must be a list"
            raise ValueError(msg)


def _balance_from_payload[Payload](payload: Payload) -> SplitwiseBalance:
    match payload:
        case dict() as balance:
            try:
                amount = Decimal(str(balance["amount"]))
            except InvalidOperation as error:
                msg = "Splitwise balance amount must be decimal"
                raise ValueError(msg) from error

            return SplitwiseBalance(
                currency_code=str(balance["currency_code"]),
                amount=amount,
            )
        case _:
            msg = "Splitwise balance must be an object"
            raise ValueError(msg)


def _optional_str[Value](value: Value | None) -> str | None:
    if value is None:
        return None
    return str(value)

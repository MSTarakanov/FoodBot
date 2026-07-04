from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import httpx

from office_food_bot.models import SplitwiseMember

SPLITWISE_API_BASE_URL = "https://secure.splitwise.com/api/v3.0"


class SplitwiseLookupKind(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SplitwiseLookupResult:
    kind: SplitwiseLookupKind
    member: SplitwiseMember | None = None


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
                    headers={"Authorization": f"Bearer {self._api_key}"},
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
        if not email or self._client is None or self._group_id is None:
            return SplitwiseLookupResult(SplitwiseLookupKind.UNAVAILABLE)

        try:
            members = await self._client.group_members(self._group_id)
        except SplitwiseUnavailableError:
            return SplitwiseLookupResult(SplitwiseLookupKind.UNAVAILABLE)

        for member in members:
            if normalize_email(member.email) == email:
                return SplitwiseLookupResult(SplitwiseLookupKind.FOUND, member)

        return SplitwiseLookupResult(SplitwiseLookupKind.NOT_FOUND)


def normalize_email(raw_email: str) -> str:
    return raw_email.strip().lower()


def _members_from_group_payload(payload: object) -> tuple[SplitwiseMember, ...]:
    if not isinstance(payload, dict):
        msg = "Splitwise group payload must be an object"
        raise ValueError(msg)

    group = payload["group"]
    if not isinstance(group, dict):
        msg = "Splitwise group must be an object"
        raise ValueError(msg)

    members = group["members"]
    if not isinstance(members, list):
        msg = "Splitwise group members must be a list"
        raise ValueError(msg)

    return tuple(_member_from_payload(member) for member in members)


def _member_from_payload(payload: object) -> SplitwiseMember:
    if not isinstance(payload, dict):
        msg = "Splitwise member must be an object"
        raise ValueError(msg)

    return SplitwiseMember(
        splitwise_user_id=int(payload["id"]),
        first_name=str(payload.get("first_name") or ""),
        last_name=_optional_str(payload.get("last_name")),
        email=str(payload["email"]),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)

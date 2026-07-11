from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from office_food_bot.models import StoredPoll
from office_food_bot.repositories import PollRepository
from office_food_bot.services.polls import PollAction, PollDefinition, PollDefinitionCatalog


@dataclass(frozen=True, slots=True)
class PollActionRequest:
    poll_id: str
    chat_id: int
    action: PollAction
    context_date: date


class PollTrackingService:
    def __init__(
        self,
        polls: PollRepository,
        definitions: PollDefinitionCatalog,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._polls = polls
        self._definitions = definitions
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._consumed_actions: set[tuple[str, PollAction]] = set()

    def register_poll(
        self,
        poll_id: str,
        chat_id: int,
        message_id: int,
        definition: PollDefinition,
        context_date: date,
    ) -> None:
        self._polls.save(
            StoredPoll(
                poll_id=poll_id,
                chat_id=chat_id,
                message_id=message_id,
                kind=definition.kind,
                context_date=context_date,
                published_at=self._clock(),
            )
        )

    def consume_action_requests(
        self,
        poll_id: str,
        telegram_user_id: int,
        selected_option_ids: tuple[int, ...],
    ) -> tuple[PollActionRequest, ...]:
        stored_poll = self._polls.get(poll_id)
        if stored_poll is None:
            return ()
        definition = self._definitions.get(stored_poll.kind)
        selected_keys = definition.known_keys_for_indices(selected_option_ids)
        new_keys = self._polls.replace_selected_options(
            poll_id,
            telegram_user_id,
            selected_keys,
            self._clock(),
        )
        requests: list[PollActionRequest] = []
        for key in new_keys:
            action = definition.action_for(key)
            if action is None:
                continue
            consumed_key = (poll_id, action)
            if consumed_key in self._consumed_actions:
                continue
            self._consumed_actions.add(consumed_key)
            requests.append(
                PollActionRequest(
                    poll_id,
                    stored_poll.chat_id,
                    action,
                    stored_poll.context_date,
                )
            )
        return tuple(requests)

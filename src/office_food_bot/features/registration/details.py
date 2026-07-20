from __future__ import annotations

from office_food_bot.application.splitwise.models import SplitwiseMember
from office_food_bot.application.users.models import RegisteredUser
from office_food_bot.features.registration.models import (
    RegistrationDetails,
    SplitwiseConnection,
)


def registration_details(
    display_name: str,
    splitwise_member: SplitwiseMember | None,
) -> RegistrationDetails:
    return RegistrationDetails(
        display_name=display_name,
        splitwise=splitwise_connection_from_member(splitwise_member),
    )


def registration_details_from_user(
    user: RegisteredUser,
    splitwise_member: SplitwiseMember | None,
) -> RegistrationDetails:
    return registration_details(user.display_name, splitwise_member)


def registration_details_changed(
    previous_details: RegistrationDetails,
    current_details: RegistrationDetails,
) -> bool:
    return (
        previous_details.display_name != current_details.display_name
        or not same_splitwise_connection(
            previous_details.splitwise,
            current_details.splitwise,
        )
    )


def same_splitwise_connection(
    first: SplitwiseConnection | None,
    second: SplitwiseConnection | None,
) -> bool:
    if first is None or second is None:
        return first is None and second is None
    return (
        first.splitwise_user_id == second.splitwise_user_id
        and _optional_email_key(first.email) == _optional_email_key(second.email)
    )


def splitwise_connection_from_member(
    splitwise_member: SplitwiseMember | None,
) -> SplitwiseConnection | None:
    if splitwise_member is None:
        return None
    return SplitwiseConnection(
        splitwise_user_id=splitwise_member.splitwise_user_id,
        email=splitwise_member.email,
    )


def _optional_email_key(email: str | None) -> str | None:
    if email is None:
        return None
    return email.casefold()

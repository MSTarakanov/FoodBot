from __future__ import annotations

from office_food_bot.flows.contracts import (
    ChoiceFlowView,
    ClosingFlowView,
    FlowView,
    TextFlowView,
)
from office_food_bot.flows.registration.validation import (
    RegistrationStepError,
    RegistrationStepErrorCode,
)
from office_food_bot.models import (
    InvitationPreferences,
    RegisteredUser,
    RegistrationDetails,
    SplitwiseConnection,
    SplitwiseMember,
    TelegramProfile,
)
from office_food_bot.services.registration import RegistrationService

NAME_PROMPT_TEXT = (
    "Напиши имя одним сообщением. Например: Максим\n"
    "Чтобы выйти из регистрации, отправь /cancel или запусти другую команду."
)
SPLITWISE_PROMPT_TEXT = (
    "Пришли email аккаунта Splitwise, чтобы я проверил тебя в офисной группе.\n"
    "Можно написать «Пропустить»."
)
SPLITWISE_SKIP_WARNING_TEXT = (
    "Splitwise не указан. Когда /balance будет подключен, она не сможет учитывать тебя "
    "без привязки."
)
SPLITWISE_SKIP_CHOICES = ("Пропустить",)
PREFERENCE_CHOICES = ("Да", "Нет")
LUNCH_PREFERENCE_PROMPT = "Звать тебя на ланч упоминанием в общем чате?"
COFFEE_PREFERENCE_PROMPT = (
    "Звать тебя на кофе, если ты отметил в опросе, что находишься в офисе?"
)


def name_prompt_view(profile: TelegramProfile, text: str) -> ChoiceFlowView:
    suggested_display_name = " ".join(profile.first_name.split())
    return ChoiceFlowView(
        text,
        (suggested_display_name,),
        columns=1,
        one_time_keyboard=True,
    )


def splitwise_prompt_view(display_name: str) -> ChoiceFlowView:
    return ChoiceFlowView(
        f"Имя записал: {display_name}\n\n{SPLITWISE_PROMPT_TEXT}",
        SPLITWISE_SKIP_CHOICES,
        columns=1,
        one_time_keyboard=False,
    )


def splitwise_not_found_view() -> ChoiceFlowView:
    return ChoiceFlowView(
        "Не нашел такой email в офисной Splitwise-группе.\n"
        "Проверь email и пришли другой или нажми «Пропустить».\n\n"
        f"{SPLITWISE_SKIP_WARNING_TEXT}",
        SPLITWISE_SKIP_CHOICES,
        columns=1,
        one_time_keyboard=False,
    )


def splitwise_unavailable_view() -> ChoiceFlowView:
    return ChoiceFlowView(
        "Не смог проверить Splitwise прямо сейчас.\n"
        "Можно попробовать другой email позже или нажать «Пропустить».\n\n"
        f"{SPLITWISE_SKIP_WARNING_TEXT}",
        SPLITWISE_SKIP_CHOICES,
        columns=1,
        one_time_keyboard=False,
    )


def lunch_preference_view(
    splitwise_member: SplitwiseMember | None,
) -> ChoiceFlowView:
    splitwise_text = SPLITWISE_SKIP_WARNING_TEXT
    if splitwise_member is not None:
        splitwise_text = (
            f"Splitwise найден: {splitwise_member.email} "
            f"(ID {splitwise_member.splitwise_user_id})."
        )
    return ChoiceFlowView(
        f"{splitwise_text}\n\n{LUNCH_PREFERENCE_PROMPT}",
        PREFERENCE_CHOICES,
    )


def coffee_preference_view() -> ChoiceFlowView:
    return ChoiceFlowView(COFFEE_PREFERENCE_PROMPT, PREFERENCE_CHOICES)


def reregistration_confirmation_view(
    user: RegisteredUser,
    requested_display_name: str,
    splitwise_member: SplitwiseMember | None,
    previous_details: RegistrationDetails,
) -> ChoiceFlowView:
    return ChoiceFlowView(
        "Вы уже зарегистрированы.\n"
        "Текущие данные:\n"
        f"Имя: {user.display_name}\n"
        f"Telegram ID: {user.telegram_user_id}\n"
        f"Username: {_username_text(user.username)}\n"
        f"{splitwise_connection_admin_text(previous_details.splitwise)}\n"
        "\n"
        "Новые данные:\n"
        f"Имя: {requested_display_name}\n"
        f"{splitwise_admin_text(splitwise_member)}\n"
        "\n"
        "Перерегистрировать вас?",
        PREFERENCE_CHOICES,
    )


def validation_error_view(error: RegistrationStepError) -> FlowView:
    if error.code == RegistrationStepErrorCode.NAME_TEXT_REQUIRED:
        return TextFlowView("Напиши имя текстом. Например: Максим")
    if error.code == RegistrationStepErrorCode.NAME_EMPTY:
        return TextFlowView("Имя не может быть пустым. Напиши имя, например: Максим")
    if error.code == RegistrationStepErrorCode.SPLITWISE_TEXT_REQUIRED:
        return ChoiceFlowView(
            "Пришли email текстом или нажми «Пропустить».",
            SPLITWISE_SKIP_CHOICES,
            columns=1,
            one_time_keyboard=False,
        )
    if error.code == RegistrationStepErrorCode.LUNCH_CHOICE_REQUIRED:
        return ChoiceFlowView(LUNCH_PREFERENCE_PROMPT, PREFERENCE_CHOICES)
    if error.code == RegistrationStepErrorCode.COFFEE_CHOICE_REQUIRED:
        return ChoiceFlowView(COFFEE_PREFERENCE_PROMPT, PREFERENCE_CHOICES)
    if error.code == RegistrationStepErrorCode.REREGISTRATION_CHOICE_REQUIRED:
        return ChoiceFlowView("Выбери: перерегистрировать вас?", PREFERENCE_CHOICES)
    raise RuntimeError(f"Unsupported registration step error: {error.code.value}")


def registration_reply_text(
    base_text: str,
    splitwise_member: SplitwiseMember | None,
    preferences: InvitationPreferences | None = None,
) -> str:
    parts = [base_text]
    if splitwise_member is not None:
        parts.append(
            f"Splitwise найден: {splitwise_member.email} "
            f"(ID {splitwise_member.splitwise_user_id})."
        )
    else:
        parts.append(SPLITWISE_SKIP_WARNING_TEXT)
    if preferences is not None:
        parts.append(invitation_preferences_text(preferences))
    return "\n\n".join(parts)


def invitation_preferences_text(preferences: InvitationPreferences) -> str:
    lunch = "да" if preferences.lunch_enabled else "нет"
    coffee = "да" if preferences.coffee_enabled else "нет"
    return f"Звать на ланч: {lunch}.\nЗвать на кофе: {coffee}."


def admin_registration_text(
    title: str,
    *,
    telegram_user_id: int,
    current_details: RegistrationDetails,
    previous_details: RegistrationDetails | None,
    preferences: InvitationPreferences | None,
) -> str:
    if previous_details is None:
        lines = [
            title,
            f"Имя: {current_details.display_name}",
            f"Telegram ID: {telegram_user_id}",
            splitwise_connection_admin_text(current_details.splitwise),
        ]
        if preferences is not None:
            lines.append(invitation_preferences_text(preferences))
        lines.append(f"Аппрув: /approve {telegram_user_id}")
        return "\n".join(lines)

    change_lines = registration_change_lines(previous_details, current_details)
    return "\n".join(
        (
            title,
            f"Telegram ID: {telegram_user_id}",
            "Изменения:",
            *change_lines,
            f"Аппрув: /approve {telegram_user_id}",
        )
    )


def registration_change_lines(
    previous_details: RegistrationDetails,
    current_details: RegistrationDetails,
) -> tuple[str, ...]:
    lines: list[str] = []
    if previous_details.display_name != current_details.display_name:
        lines.extend(
            (
                "Имя:",
                f"Было: {previous_details.display_name}",
                f"Стало: {current_details.display_name}",
            )
        )
    if not same_splitwise_connection(
        previous_details.splitwise,
        current_details.splitwise,
    ):
        if lines:
            lines.append("")
        lines.extend(
            (
                "Splitwise:",
                f"Было: {splitwise_value_text(previous_details.splitwise)}",
                f"Стало: {splitwise_value_text(current_details.splitwise)}",
            )
        )
    if not lines:
        return ("Нет изменений.",)
    return tuple(lines)


def registration_details_from_user(
    user: RegisteredUser,
    splitwise_member: SplitwiseMember | None,
) -> RegistrationDetails:
    return RegistrationDetails(
        display_name=user.display_name,
        splitwise=splitwise_connection_from_member(splitwise_member),
    )


def registration_details_from_input(
    registration: RegistrationService,
    profile: TelegramProfile,
    raw_display_name: str,
    splitwise_member: SplitwiseMember | None,
) -> RegistrationDetails:
    return RegistrationDetails(
        display_name=registration.display_name_from_input(profile, raw_display_name),
        splitwise=splitwise_connection_from_member(splitwise_member),
    )


def registration_details_changed(
    previous_details: RegistrationDetails,
    current_details: RegistrationDetails,
) -> bool:
    return (
        previous_details.display_name != current_details.display_name
        or not same_splitwise_connection(previous_details.splitwise, current_details.splitwise)
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


def splitwise_admin_text(splitwise_member: SplitwiseMember | None) -> str:
    return splitwise_connection_admin_text(
        splitwise_connection_from_member(splitwise_member)
    )


def splitwise_connection_admin_text(splitwise: SplitwiseConnection | None) -> str:
    return f"Splitwise: {splitwise_value_text(splitwise)}"


def splitwise_value_text(splitwise: SplitwiseConnection | None) -> str:
    if splitwise is None:
        return "не указан"
    if splitwise.email is None:
        return f"email не указан (ID {splitwise.splitwise_user_id})"
    return f"{splitwise.email} (ID {splitwise.splitwise_user_id})"


def unchanged_registration_view() -> ClosingFlowView:
    return ClosingFlowView("Ваши данные не изменились. Перерегистрацию не запускаю.")


def _username_text(username: str | None) -> str:
    if username is None:
        return "не указан"
    return f"@{username}"


def _optional_email_key(email: str | None) -> str | None:
    if email is None:
        return None
    return email.casefold()

from __future__ import annotations

from typing import assert_never

from office_food_bot.invitation_models import InvitationKind, InvitationSettingReport


def render_invitation_setting(report: InvitationSettingReport) -> str:
    match report.kind:
        case InvitationKind.LUNCH:
            feature = "ланч"
            command = "lunch"
        case InvitationKind.COFFEE:
            feature = "кофе"
            command = "coffee"
        case _:
            assert_never(report.kind)
    state = "включены" if report.enabled else "выключены"
    if report.updated:
        return f"Приглашения на {feature} {state}."
    return (
        f"Приглашения на {feature}: {state}.\n\n"
        f"Изменить настройку: /{command} on или /{command} off."
    )

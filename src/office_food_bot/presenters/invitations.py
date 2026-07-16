from __future__ import annotations

from office_food_bot.invitation_models import InvitationKind, InvitationSettingReport


def render_invitation_setting(report: InvitationSettingReport) -> str:
    feature = "ланч" if report.kind == InvitationKind.LUNCH else "кофе"
    command = "lunch" if report.kind == InvitationKind.LUNCH else "coffee"
    state = "включены" if report.enabled else "выключены"
    if report.updated:
        return f"Приглашения на {feature} {state}."
    return (
        f"Приглашения на {feature}: {state}.\n\n"
        f"Изменить настройку: /{command} on или /{command} off."
    )

from __future__ import annotations

from datetime import date
from typing import assert_never

from office_food_bot.messaging import TextMessagePayload
from office_food_bot.vacation_models import VacationReport, VacationReportKind

VACATION_USAGE_TEXT = (
    "Уйти в отпуск или изменить дату: /vacation 2 или /vacation 20.07\n"
    "Выйти из отпуска: /vacation 0 или /vacation off"
)


def render_vacation_report(report: VacationReport) -> TextMessagePayload:
    match report.kind:
        case VacationReportKind.STATUS_ACTIVE:
            text = f"{_active_status(report)}\n\n{VACATION_USAGE_TEXT}"
        case VacationReportKind.STATUS_INACTIVE:
            text = f"{report.display_name} не в отпуске.\n\n{VACATION_USAGE_TEXT}"
        case VacationReportKind.CLEARED:
            text = f"{report.display_name} больше не в отпуске."
        case VacationReportKind.SET:
            text = f"{_active_status(report)} Чтобы выйти из отпуска: /vacation 0"
        case _:
            assert_never(report.kind)
    return TextMessagePayload(text)


def _active_status(report: VacationReport) -> str:
    if report.until_date is None:
        raise RuntimeError("Active vacation report has no end date")
    return f"{report.display_name} в отпуске до {_format_date(report.until_date)}."


def _format_date(day: date) -> str:
    return day.strftime("%d.%m.%Y")

from __future__ import annotations

from datetime import date

from office_food_bot.messaging import TextMessagePayload
from office_food_bot.vacation_models import VacationReport, VacationReportKind

VACATION_USAGE_TEXT = (
    "Уйти в отпуск или изменить дату: /vacation 2 или /vacation 20.07\n"
    "Выйти из отпуска: /vacation 0 или /vacation off"
)


def render_vacation_report(report: VacationReport) -> TextMessagePayload:
    if report.kind == VacationReportKind.STATUS_ACTIVE:
        text = f"{_active_status(report)}\n\n{VACATION_USAGE_TEXT}"
    elif report.kind == VacationReportKind.STATUS_INACTIVE:
        text = f"{report.display_name} не в отпуске.\n\n{VACATION_USAGE_TEXT}"
    elif report.kind == VacationReportKind.CLEARED:
        text = f"{report.display_name} больше не в отпуске."
    elif report.kind == VacationReportKind.SET:
        text = f"{_active_status(report)} Чтобы выйти из отпуска: /vacation 0"
    else:
        raise RuntimeError(f"Unsupported vacation report: {report.kind.value}")
    return TextMessagePayload(text)


def _active_status(report: VacationReport) -> str:
    if report.until_date is None:
        raise RuntimeError("Active vacation report has no end date")
    return f"{report.display_name} в отпуске до {_format_date(report.until_date)}."


def _format_date(day: date) -> str:
    return day.strftime("%d.%m.%Y")

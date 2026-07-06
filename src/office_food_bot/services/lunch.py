from __future__ import annotations

from office_food_bot.models import UserStatus
from office_food_bot.repositories import UserRepository

LUNCH_PLACE_OTHER_OPTION = "не знаю что хочу/хочу что-то другое"
LUNCH_POLL_QUESTION = "Обед в офисе сегодня"
LUNCH_POLL_OPTIONS = (
    "са собом",
    "кушаю в офисе",
    "заказал бы что-то",
    "сижу дома",
    "поел/поем самостоятельно",
    "не решил еще",
    "ахахахахаххаахаха",
)
LUNCH_PLACE_POLL_QUESTION = "Что едим / заказываем?"
LUNCH_PLACE_POLL_OPTIONS = (
    "30 этаж",
    "макдонелдс",
    "домашняя еда",
    LUNCH_PLACE_OTHER_OPTION,
    "посмотреть результаты",
)
LUNCH_PLACE_OTHER_OPTION_INDEX = LUNCH_PLACE_POLL_OPTIONS.index(LUNCH_PLACE_OTHER_OPTION)
LUNCH_OTHER_FOOD_POLL_QUESTION = "Закажем ..."
LUNCH_OTHER_FOOD_POLL_OPTIONS = (
    "другой бургер",
    "шаурма",
    "поке",
    "пицца",
)


class LunchService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def poll_block_reason(self, telegram_user_id: int) -> str | None:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."
        return None

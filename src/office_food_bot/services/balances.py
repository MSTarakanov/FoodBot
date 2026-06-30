from __future__ import annotations

from office_food_bot.models import UserStatus
from office_food_bot.repositories import UserRepository


class BalanceService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def balance(self, telegram_user_id: int) -> str:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            return "Сначала зарегистрируйся: /register Имя"
        if user.status == UserStatus.PENDING:
            return "Регистрация еще ждет аппрува."
        if user.status != UserStatus.ACTIVE:
            return "Регистрация сейчас неактивна."
        if self._users.count_splitwise_users() == 0:
            return "Splitwise пока не подключен."
        return "Splitwise подключим следующим шагом."

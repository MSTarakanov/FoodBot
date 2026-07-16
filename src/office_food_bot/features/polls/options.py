from enum import StrEnum
from typing import Self


class PollOption(StrEnum):
    display_value: str

    def __new__(cls, value: str, display_value: str) -> Self:
        member = str.__new__(cls, value)
        member._value_ = value
        member.display_value = display_value
        return member

    @classmethod
    def from_value(cls, value: str) -> Self:
        for option in cls:
            if option.value == value:
                return option
        msg = f"Unknown poll option value: {value}"
        raise ValueError(msg)

    LUNCH_BRING_OWN = ("lunch_bring_own", "са собом")
    LUNCH_EAT_IN_OFFICE = ("lunch_eat_in_office", "кушаю в офисе")
    LUNCH_WOULD_ORDER = ("lunch_would_order", "заказал бы что-то")
    LUNCH_STAY_HOME = ("lunch_stay_home", "сижу дома")
    LUNCH_EAT_INDEPENDENTLY = (
        "lunch_eat_independently",
        "поел/поем самостоятельно",
    )
    LUNCH_UNDECIDED = ("lunch_undecided", "не решил еще")
    LUNCH_NOT_WORKING = ("lunch_not_working", "ахахахахаххаахаха")
    LUNCH_PLACE_SKYLINE_30_FLOOR = (
        "lunch_place_skyline_30_floor",
        "30 этаж",
    )
    LUNCH_PLACE_MCDONALDS = ("lunch_place_mcdonalds", "макдонелдс")
    LUNCH_PLACE_HOME_FOOD = ("lunch_place_home_food", "домашняя еда")
    LUNCH_PLACE_ROSE_BEREZKA = ("lunch_place_rose_berezka", "березка")
    LUNCH_PLACE_ROSE_SALATNITSA = (
        "lunch_place_rose_salatnitsa",
        "салатница",
    )
    LUNCH_PLACE_EAT_OUT = (
        "lunch_place_eat_out",
        "сходил бы куда-то поесть рядом",
    )
    LUNCH_PLACE_OTHER = (
        "lunch_place_other",
        "не знаю что хочу/хочу что-то другое",
    )
    LUNCH_PLACE_VIEW_RESULTS = (
        "lunch_place_view_results",
        "посмотреть результаты",
    )
    OTHER_FOOD_BURGER = ("other_food_burger", "другой бургер")
    OTHER_FOOD_SHAWARMA = ("other_food_shawarma", "шаурма")
    OTHER_FOOD_POKE = ("other_food_poke", "поке")
    OTHER_FOOD_PIZZA = ("other_food_pizza", "пицца")

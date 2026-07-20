from __future__ import annotations

from enum import StrEnum


class CommonErrorCode(StrEnum):
    MISSING_TELEGRAM_IDENTITY = "missing_telegram_identity"
    PRIVATE_CHAT_REQUIRED = "private_chat_required"
    GROUP_CHAT_REQUIRED = "group_chat_required"
    ADMIN_REQUIRED = "admin_required"
    REGISTRATION_REQUIRED = "registration_required"
    REGISTRATION_PENDING = "registration_pending"
    REGISTRATION_INACTIVE = "registration_inactive"


class InputErrorCode(StrEnum):
    MISSING = "missing"
    INVALID_FORMAT = "invalid_format"
    INVALID_CHOICE = "invalid_choice"
    OUT_OF_RANGE = "out_of_range"
    REVERSED_RANGE = "reversed_range"

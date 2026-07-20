from __future__ import annotations

from enum import StrEnum


class ActiveUserErrorCode(StrEnum):
    NOT_REGISTERED = "not_registered"
    PENDING_APPROVAL = "pending_approval"
    INACTIVE = "inactive"

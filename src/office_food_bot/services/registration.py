from __future__ import annotations

from dataclasses import dataclass

from office_food_bot.models import (
    ApprovalKind,
    KnownTelegramAccount,
    PendingRegistration,
    RegisteredUser,
    RegistrationDetails,
    RegistrationKind,
    SplitwiseConnection,
    SplitwiseMember,
    TelegramProfile,
    UserStatus,
)
from office_food_bot.repositories import (
    RegistrationRequestRepository,
    TelegramAccountRepository,
    UserRepository,
    normalize_display_name,
)

REGISTRATION_SUGGESTIONS_LIMIT = 10


@dataclass(frozen=True)
class RegistrationResult:
    kind: RegistrationKind
    user: RegisteredUser
    previous_details: RegistrationDetails | None = None


@dataclass(frozen=True)
class ApprovalResult:
    kind: ApprovalKind
    user: RegisteredUser | None


class RegistrationService:
    def __init__(
        self,
        users: UserRepository,
        telegram_accounts: TelegramAccountRepository,
        registration_requests: RegistrationRequestRepository,
        admin_ids: frozenset[int],
    ) -> None:
        self._users = users
        self._telegram_accounts = telegram_accounts
        self._registration_requests = registration_requests
        self.admin_ids = admin_ids

    def register(
        self,
        profile: TelegramProfile,
        raw_display_name: str,
        splitwise_member: SplitwiseMember | None,
    ) -> RegistrationResult:
        display_name = _clean_display_name(profile, raw_display_name)
        existing_user = self._users.get_by_telegram_id(profile.telegram_user_id)
        if existing_user is not None:
            previous_details = self._users.get_registration_details_by_telegram_id(
                profile.telegram_user_id,
            )
            if existing_user.status == UserStatus.ABANDONED:
                user = self._save_pending_registration(
                    profile,
                    display_name,
                    splitwise_member,
                )
                return RegistrationResult(RegistrationKind.CREATED, user)

            if existing_user.status == UserStatus.PENDING:
                if previous_details is not None and not _has_registration_changes(
                    previous_details,
                    display_name,
                    splitwise_member,
                ):
                    self._users.refresh_telegram_profile(profile)
                    self._registration_requests.clear(profile.telegram_user_id)
                    refreshed_user = self._users.get_by_telegram_id(
                        profile.telegram_user_id,
                    )
                    if refreshed_user is None:
                        msg = "Refreshed user was not found"
                        raise RuntimeError(msg)
                    return RegistrationResult(
                        RegistrationKind.ALREADY_PENDING,
                        refreshed_user,
                        previous_details,
                    )

                user = self._save_pending_registration(
                    profile,
                    display_name,
                    splitwise_member,
                )
                return RegistrationResult(
                    RegistrationKind.UPDATED_PENDING,
                    user,
                    previous_details,
                )

            self._users.refresh_telegram_profile(profile)
            refreshed_user = self._users.get_by_telegram_id(profile.telegram_user_id)
            if refreshed_user is None:
                msg = "Refreshed user was not found"
                raise RuntimeError(msg)
            return RegistrationResult(
                _registration_kind_for(refreshed_user),
                refreshed_user,
                previous_details,
            )

        user = self._save_pending_registration(profile, display_name, splitwise_member)
        return RegistrationResult(RegistrationKind.CREATED, user)

    def re_register(
        self,
        profile: TelegramProfile,
        raw_display_name: str,
        splitwise_member: SplitwiseMember | None,
    ) -> RegisteredUser:
        return self._save_pending_registration(
            profile,
            self.display_name_from_input(profile, raw_display_name),
            splitwise_member,
        )

    def request_registration(self, profile: TelegramProfile) -> None:
        self._telegram_accounts.remember(profile)
        self._registration_requests.request(profile.telegram_user_id)

    def display_name_from_input(self, profile: TelegramProfile, raw_display_name: str) -> str:
        return _clean_display_name(profile, raw_display_name)

    def registration_profile_for_telegram_id(self, telegram_user_id: int) -> TelegramProfile:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None:
            telegram_account = self._telegram_accounts.get(telegram_user_id)
            if telegram_account is not None:
                return _telegram_profile_from_known_account(telegram_account)

            return TelegramProfile(
                telegram_user_id=telegram_user_id,
                username=None,
                first_name=f"Telegram ID {telegram_user_id}",
                last_name=None,
            )

        return TelegramProfile(
            telegram_user_id=user.telegram_user_id,
            username=user.username,
            first_name=user.first_name or user.display_name,
            last_name=user.last_name,
        )

    def request_registration_block_reason(self, telegram_user_id: int) -> str | None:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None or user.status == UserStatus.ABANDONED:
            return None
        if user.status == UserStatus.PENDING:
            return (
                "Заявка уже ждет аппрува. "
                "Если хотите отменить регистрацию, отправьте /quit."
            )
        if user.status == UserStatus.ACTIVE:
            return (
                "Вы уже зарегистрированы. "
                "Если хотите отрегистрироваться, отправьте /quit."
            )
        return (
            "Регистрация сейчас недоступна. "
            "Если хотите отрегистрироваться, отправьте /quit."
        )

    def quit_registration(self, telegram_user_id: int) -> bool:
        user = self._users.get_by_telegram_id(telegram_user_id)
        if user is None or user.status == UserStatus.ABANDONED:
            return False
        return self._users.abandon_by_telegram_id(telegram_user_id) is not None

    def approve(
        self,
        approver_telegram_user_id: int,
        target_telegram_user_id: int,
    ) -> ApprovalResult:
        if not self.can_approve(approver_telegram_user_id):
            return ApprovalResult(ApprovalKind.FORBIDDEN, None)

        user = self._users.approve_by_telegram_id(target_telegram_user_id)
        if user is None:
            return ApprovalResult(ApprovalKind.NOT_FOUND, None)
        return ApprovalResult(ApprovalKind.APPROVED, user)

    def can_approve(self, telegram_user_id: int) -> bool:
        return telegram_user_id in self.admin_ids or self._users.is_active_admin(telegram_user_id)

    def list_pending_requests(
        self,
        requester_telegram_user_id: int,
    ) -> tuple[PendingRegistration, ...]:
        if not self.can_approve(requester_telegram_user_id):
            return ()
        return self._users.list_pending_registrations()

    def list_requested_telegram_accounts(
        self,
        requester_telegram_user_id: int,
    ) -> tuple[KnownTelegramAccount, ...]:
        if not self.can_approve(requester_telegram_user_id):
            return ()
        return self._registration_requests.list_requested(REGISTRATION_SUGGESTIONS_LIMIT)

    def list_seen_telegram_accounts(
        self,
        requester_telegram_user_id: int,
    ) -> tuple[KnownTelegramAccount, ...]:
        if not self.can_approve(requester_telegram_user_id):
            return ()
        return self._telegram_accounts.list_seen(REGISTRATION_SUGGESTIONS_LIMIT)

    def _save_pending_registration(
        self,
        profile: TelegramProfile,
        display_name: str,
        splitwise_member: SplitwiseMember | None,
    ) -> RegisteredUser:
        user = self._users.save_pending_registration(profile, display_name, splitwise_member)
        self._registration_requests.clear(profile.telegram_user_id)
        return user


def _telegram_profile_from_known_account(
    telegram_account: KnownTelegramAccount,
) -> TelegramProfile:
    return TelegramProfile(
        telegram_user_id=telegram_account.telegram_user_id,
        username=telegram_account.username,
        first_name=telegram_account.first_name
        or f"Telegram ID {telegram_account.telegram_user_id}",
        last_name=telegram_account.last_name,
    )


def _registration_kind_for(user: RegisteredUser) -> RegistrationKind:
    if user.status == UserStatus.ACTIVE:
        return RegistrationKind.ALREADY_ACTIVE
    if user.status == UserStatus.PENDING:
        return RegistrationKind.ALREADY_PENDING
    return RegistrationKind.BLOCKED


def _clean_display_name(profile: TelegramProfile, raw_display_name: str) -> str:
    display_name = normalize_display_name(raw_display_name)
    if not display_name:
        display_name = _telegram_display_name(profile)
    if len(display_name) > 64:
        display_name = display_name[:64].rstrip()
    return display_name


def _telegram_display_name(profile: TelegramProfile) -> str:
    return normalize_display_name(
        " ".join(
            part
            for part in (profile.first_name, profile.last_name)
            if part is not None
        )
    )


def _has_registration_changes(
    previous_details: RegistrationDetails,
    display_name: str,
    splitwise_member: SplitwiseMember | None,
) -> bool:
    return (
        previous_details.display_name != display_name
        or not _same_splitwise_connection(
            previous_details.splitwise,
            _splitwise_connection_from_member(splitwise_member),
        )
    )


def _same_splitwise_connection(
    first: SplitwiseConnection | None,
    second: SplitwiseConnection | None,
) -> bool:
    if first is None or second is None:
        return first is None and second is None
    return (
        first.splitwise_user_id == second.splitwise_user_id
        and _optional_email_key(first.email) == _optional_email_key(second.email)
    )


def _optional_email_key(email: str | None) -> str | None:
    if email is None:
        return None
    return email.casefold()


def _splitwise_connection_from_member(
    splitwise_member: SplitwiseMember | None,
) -> SplitwiseConnection | None:
    if splitwise_member is None:
        return None
    return SplitwiseConnection(
        splitwise_user_id=splitwise_member.splitwise_user_id,
        email=splitwise_member.email,
    )

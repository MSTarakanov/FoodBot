from office_food_bot.models import RegisteredUser


def format_user_reference(user: RegisteredUser) -> str:
    if user.username is not None:
        return f"@{user.username}"
    return user.display_name

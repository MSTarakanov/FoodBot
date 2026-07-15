from office_food_bot.previews.balance import BALANCE_FULL_PREVIEW
from office_food_bot.previews.catalog import MessagePreviewCatalog

MESSAGE_PREVIEWS = MessagePreviewCatalog((BALANCE_FULL_PREVIEW,))

__all__ = ["MESSAGE_PREVIEWS"]

from __future__ import annotations

import pytest

from office_food_bot.messaging import TextMessagePayload
from office_food_bot.previews.catalog import MessagePreviewCatalog, PreviewDefinition
from office_food_bot.previews.registry import MESSAGE_PREVIEWS


def test_preview_catalog_resolves_registered_definition() -> None:
    expected = TextMessagePayload("preview")
    catalog = MessagePreviewCatalog(
        (PreviewDefinition("example", lambda: expected),)
    )

    assert catalog.cases == ("example",)
    assert catalog.render(" Example ") == expected


def test_preview_catalog_rejects_unknown_case_and_lists_available_cases() -> None:
    assert MESSAGE_PREVIEWS.render("unknown") is None
    assert MESSAGE_PREVIEWS.help_text() == (
        "Доступные тестовые сообщения:\n/test balance-full"
    )


def test_preview_catalog_requires_unique_case_names() -> None:
    definition = PreviewDefinition("duplicate", lambda: TextMessagePayload("preview"))

    with pytest.raises(ValueError, match="must be unique"):
        MessagePreviewCatalog((definition, definition))

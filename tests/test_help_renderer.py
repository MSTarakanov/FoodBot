from office_food_bot.commands.definitions import (
    HelpSection,
    VisibleCommandHelpEntry,
)
from office_food_bot.commands.help_renderer import HelpRenderer


def test_help_renderer_bolds_headings_and_escapes_html_content() -> None:
    entry = VisibleCommandHelpEntry(
        "example",
        (),
        "/example <value>",
        "сравнить A < B",
        HelpSection.MAIN,
    )

    rendered = HelpRenderer().render((entry,))

    assert rendered == (
        "<b>Команды:</b>\n\n"
        "<b>Основные:</b>\n"
        "/example &lt;value&gt; - сравнить A &lt; B"
    )

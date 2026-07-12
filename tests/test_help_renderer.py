from office_food_bot.commands.definitions import (
    CommandDefinition,
    CommandScope,
    HelpSection,
)
from office_food_bot.commands.help_renderer import HelpRenderer


def test_help_renderer_bolds_headings_and_escapes_html_content() -> None:
    definition = CommandDefinition(
        "example",
        "сравнить A < B",
        "/example <value>",
        CommandScope.ANY,
        HelpSection.MAIN,
    )

    rendered = HelpRenderer().render((definition,))

    assert rendered == (
        "<b>Команды:</b>\n\n"
        "<b>Основные:</b>\n"
        "/example &lt;value&gt; - сравнить A &lt; B"
    )

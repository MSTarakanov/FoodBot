from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from html import escape

from office_food_bot.commands.definitions import CommandDefinition, HelpSection


@dataclass(frozen=True, slots=True)
class HelpLine:
    section: HelpSection
    usage: str
    description: str


class HelpRenderer:
    def render(self, definitions: Iterable[CommandDefinition]) -> str:
        lines = tuple(
            line
            for definition in definitions
            for line in self._definition_lines(definition)
        )
        sections = tuple(
            self._render_section(section, lines)
            for section in HelpSection
            if any(line.section == section for line in lines)
        )
        return "<b>Команды:</b>\n\n" + "\n\n".join(sections)

    def _definition_lines(
        self,
        definition: CommandDefinition,
    ) -> tuple[HelpLine, ...]:
        primary = HelpLine(
            definition.help_section,
            self._usage_with_aliases(definition, definition.usage),
            definition.description,
        )
        additional = tuple(
            HelpLine(
                entry.section,
                self._usage_with_aliases(definition, entry.usage),
                entry.description,
            )
            for entry in definition.additional_help
        )
        return (primary, *additional)

    def _render_section(
        self,
        section: HelpSection,
        lines: tuple[HelpLine, ...],
    ) -> str:
        entries = "\n".join(
            f"{escape(line.usage)} - {escape(line.description)}"
            for line in lines
            if line.section == section
        )
        return f"<b>{escape(section.value)}:</b>\n{entries}"

    def _usage_with_aliases(
        self,
        definition: CommandDefinition,
        usage: str,
    ) -> str:
        alias_usages = tuple(
            usage.replace(f"/{definition.name}", f"/{alias}")
            for alias in definition.text_aliases
        )
        if not alias_usages:
            return usage
        return f"{usage} (также {'; '.join(alias_usages)})"


HELP_RENDERER = HelpRenderer()

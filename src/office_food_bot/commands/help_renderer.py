from __future__ import annotations

from collections.abc import Iterable
from html import escape

from office_food_bot.commands.definitions import HelpSection, VisibleCommandHelpEntry


class HelpRenderer:
    def render(self, entries: Iterable[VisibleCommandHelpEntry]) -> str:
        lines = tuple(entries)
        sections = tuple(
            self._render_section(section, lines)
            for section in HelpSection
            if any(line.section == section for line in lines)
        )
        return "<b>Команды:</b>\n\n" + "\n\n".join(sections)

    def _render_section(
        self,
        section: HelpSection,
        lines: tuple[VisibleCommandHelpEntry, ...],
    ) -> str:
        entries = "\n".join(
            f"{escape(self._usage_with_aliases(line))} - {escape(line.description)}"
            for line in lines
            if line.section == section
        )
        return f"<b>{escape(section.value)}:</b>\n{entries}"

    def _usage_with_aliases(
        self,
        entry: VisibleCommandHelpEntry,
    ) -> str:
        alias_usages = tuple(
            entry.usage.replace(f"/{entry.command_name}", f"/{alias}")
            for alias in entry.text_aliases
        )
        if not alias_usages:
            return entry.usage
        return f"{entry.usage} (также {'; '.join(alias_usages)})"


HELP_RENDERER = HelpRenderer()

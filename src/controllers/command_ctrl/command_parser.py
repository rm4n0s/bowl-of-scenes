import json
import re
from dataclasses import dataclass
from typing import Any, Optional, Set


@dataclass
class GroupSelection:
    """Represents a group with optional inclusions/exclusions"""

    group_code_name: str
    include_only: Optional[list[str]] = None  # Specific items to include
    exclude: Optional[Set[str]] = None  # Items to exclude
    is_merged: bool = False  # True if multiple groups merged with 'and'
    merged_groups: Optional[list[dict[str, Any]]] = (
        None  # List of group configs if merged
    )

    def to_dict(self):
        result = {
            "group_code_name": self.group_code_name,
            "include_only": self.include_only,
            "exclude": list(self.exclude) if self.exclude else None,
        }
        if self.is_merged:
            result["is_merged"] = True
            result["merged_groups"] = self.merged_groups
        return result


@dataclass
class ParsedCommand:
    """Represents a parsed command"""

    server_code_name: str
    generator_code_name: str
    group_selections: list[GroupSelection]
    fixers: Optional[list[str]] = None

    def to_dict(self):
        result = {
            "server_code_name": self.server_code_name,
            "generator_code_name": self.generator_code_name,
            "group_selections": [gs.to_dict() for gs in self.group_selections],
        }
        if self.fixers:
            result["fixers"] = self.fixers
        return result

    def to_json(self, indent=2):
        """Compile to JSON format"""
        return json.dumps(self.to_dict(), indent=indent)


class PromptLanguageParser:
    """Parser for the prompt mini-language"""

    def __init__(self):
        # Regex patterns
        self.server_workflow_pattern = r"(\w+)\s*-\$\s*(\w+)\s*:\s*(.+)"

    def parse(self, command: str) -> ParsedCommand:
        """
        Parse a command string into a structured format

        Args:
            command: String like "server1 -$ workflow1: char_group x emotion_group > fixer1"

        Returns:
            ParsedCommand object
        """
        # Remove extra whitespace
        command = " ".join(command.split())

        # Match server -$ workflow : groups
        match = re.match(self.server_workflow_pattern, command)
        if not match:
            raise ValueError(f"Invalid command syntax: {command}")

        server_code = match.group(1)
        workflow_code = match.group(2)
        rest = match.group(3)

        # Split by '>' to separate groups from fixers
        if " > " in rest:
            parts = rest.split(" > ")
            groups_part = parts[0].strip()
            fixers = [f.strip() for f in parts[1:]]
        else:
            groups_part = rest
            fixers = None

        # Parse groups
        group_selections = self._parse_groups(groups_part)

        return ParsedCommand(
            server_code_name=server_code,
            generator_code_name=workflow_code,
            group_selections=group_selections,
            fixers=fixers,
        )

    def _parse_groups(self, groups_part: str) -> list[GroupSelection]:
        """Parse the groups portion of the command"""
        # Split by ' x ' (with spaces) to get individual group expressions
        group_expressions = [g.strip() for g in groups_part.split(" x ")]

        selections = []
        for expr in group_expressions:
            # Check if this expression has 'and' (merge groups)
            if " and " in expr:
                selection = self._parse_merged_groups(expr)
            else:
                selection = self._parse_group_expression(expr)
            selections.append(selection)

        return selections

    def _parse_merged_groups(self, expr: str) -> GroupSelection:
        """
        Parse merged groups expression like:
        - group_1 and group_2
        - group_1(item1) and group_2 and group_3(~item3)
        """
        # Split by ' and '
        group_parts = [g.strip() for g in expr.split(" and ")]

        merged_groups = []
        all_group_names = []

        for part in group_parts:
            # Parse each group separately
            group_name = None
            include_items = None
            exclude_items = set()

            # Find group name (first word)
            parts = part.split("(", 1)
            group_name = parts[0].strip()
            all_group_names.append(group_name)

            if len(parts) > 1:
                # Has parentheses - parse include/exclude
                paren_groups = re.findall(r"\(([^)]+)\)", part)

                for paren_group in paren_groups:
                    items = [item.strip() for item in paren_group.split(",")]

                    # Check if this is exclusion (starts with ~)
                    if items and items[0].startswith("~"):
                        # Exclusion group
                        exclude_items.update(item.lstrip("~") for item in items)
                    else:
                        # Inclusion group (specific items)
                        include_items = items

            merged_groups.append(
                {
                    "group_code_name": group_name,
                    "include_only": include_items,
                    "exclude": list(exclude_items) if exclude_items else None,
                }
            )

        # Return a merged selection
        return GroupSelection(
            group_code_name="+".join(all_group_names),
            include_only=None,
            exclude=None,
            is_merged=True,
            merged_groups=merged_groups,
        )

    def _parse_group_expression(self, expr: str) -> GroupSelection:
        """
        Parse a single group expression like:
        - character_group
        - character_group (alice, bob)
        - emotion_group (~sad, ~sob)
        """
        group_name = None
        include_items = None
        exclude_items = set()

        # Find group name (first word)
        parts = expr.split("(", 1)
        group_name = parts[0].strip()

        if len(parts) > 1:
            # Has parentheses - parse include/exclude
            paren_groups = re.findall(r"\(([^)]+)\)", expr)

            for paren_group in paren_groups:
                items = [item.strip() for item in paren_group.split(",")]

                # Check if this is exclusion (starts with ~)
                if items and items[0].startswith("~"):
                    # Exclusion group
                    exclude_items.update(item.lstrip("~") for item in items)
                else:
                    # Inclusion group (specific items)
                    include_items = items

        return GroupSelection(
            group_code_name=group_name,
            include_only=include_items,
            exclude=exclude_items if exclude_items else None,
        )

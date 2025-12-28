import json
import re
from dataclasses import dataclass
from typing import Optional, Set


@dataclass
class GroupSelection:
    """Represents a group with optional inclusions/exclusions"""

    group_code_name: str
    include_only: Optional[list[str]] = None  # Specific items to include
    exclude: Optional[Set[str]] = None  # Items to exclude

    def to_dict(self):
        return {
            "group_code_name": self.group_code_name,
            "include_only": self.include_only,
            "exclude": list(self.exclude) if self.exclude else None,
        }


@dataclass
class ParsedCommand:
    """Represents a parsed command"""

    server_code_name: str
    workflow_code_name: str
    group_selections: list[GroupSelection]

    def to_dict(self):
        return {
            "server_code_name": self.server_code_name,
            "workflow_code_name": self.workflow_code_name,
            "group_selections": [gs.to_dict() for gs in self.group_selections],
        }

    def to_json(self, indent=2):
        """Compile to JSON format"""
        return json.dumps(self.to_dict(), indent=indent)


class PromptLanguageParser:
    """Parser for the prompt mini-language"""

    def __init__(self):
        # Regex patterns
        self.server_workflow_pattern = r"(\w+)\s*-\$\s*(\w+)\s*:\s*(.+)"
        self.group_pattern = r"(\w+)(?:\s*\(([^)]+)\))?(?:\s*\(~([^)]+)\))?"

    def parse(self, command: str) -> ParsedCommand:
        """
        Parse a command string into a structured format

        Args:
            command: String like "server1 -$ workflow1: char_group x emotion_group (~sad,~sob)"

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
        groups_part = match.group(3)

        # Parse groups (split by 'x')
        group_selections = self._parse_groups(groups_part)

        return ParsedCommand(
            server_code_name=server_code,
            workflow_code_name=workflow_code,
            group_selections=group_selections,
        )

    def _parse_groups(self, groups_part: str) -> list[GroupSelection]:
        """Parse the groups portion of the command"""
        # Split by 'x' to get individual group expressions
        group_expressions = [g.strip() for g in groups_part.split("x")]

        selections = []
        for expr in group_expressions:
            selection = self._parse_group_expression(expr)
            selections.append(selection)

        return selections

    def _parse_group_expression(self, expr: str) -> GroupSelection:
        """
        Parse a single group expression like:
        - character_group
        - character_group (alice, bob)
        - emotion_group (~sad, ~sob)
        """
        # Pattern to match: group_name (item1, item2) (~item3, ~item4)
        # We need to handle both include and exclude patterns

        group_name = None
        include_items = None
        exclude_items = set()

        # Find group name (first word)
        parts = expr.split("(", 1)
        group_name = parts[0].strip()

        if len(parts) > 1:
            # Has parentheses - parse include/exclude
            paren_content = parts[1]

            # Split by ) to handle multiple parentheses groups
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

"""
Parser for the prompt mini-language
Supports syntax: server_code -$ workflow_code: group1 x group2 > fixer1 > fixer2
"""

import json
import re
from dataclasses import dataclass
from typing import Optional, Set


@dataclass
class GroupSelection:
    """Represents a group with optional inclusions/exclusions"""

    group_code_name: str
    include_only: Optional[list[str]] = None
    exclude: Optional[Set[str]] = None
    is_merged: bool = False
    merged_groups: Optional[list[dict]] = None
    is_regioned: bool = False
    region_group_selections: Optional[dict[str, list["GroupSelection"]]] = None

    def to_dict(self):
        result = {
            "group_code_name": self.group_code_name,
            "include_only": self.include_only,
            "exclude": list(self.exclude) if self.exclude else None,
        }
        if self.is_merged:
            result["is_merged"] = True
            result["merged_groups"] = self.merged_groups
        if self.is_regioned:
            assert self.region_group_selections
            result["is_regioned"] = True
            result["region_group_selections"] = {
                region: [gs.to_dict() for gs in selections]
                for region, selections in self.region_group_selections.items()
            }
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
        # Handle region groups first (they contain ' x ' inside {})
        # Split by ' x ' but respect {} boundaries
        group_expressions = []
        current = []
        depth = 0

        i = 0
        while i < len(groups_part):
            char = groups_part[i]

            if char == "{":
                depth += 1
                current.append(char)
            elif char == "}":
                depth -= 1
                current.append(char)
            elif (
                char == " "
                and i + 2 < len(groups_part)
                and groups_part[i : i + 3] == " x "
                and depth == 0
            ):
                # Found ' x ' outside braces
                group_expressions.append("".join(current).strip())
                current = []
                i += 2  # Skip ' x '
            else:
                current.append(char)

            i += 1

        if current:
            group_expressions.append("".join(current).strip())

        selections = []
        for expr in group_expressions:
            # Check if this expression has region groups (contains {)
            if "{" in expr:
                selection = self._parse_region_groups(expr)
            # Check if this expression has 'and' (merge groups)
            elif " and " in expr:
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

    def _parse_region_groups(self, expr: str) -> GroupSelection:
        """
        Parse region groups expression like:
        - group_1{red: group_2 x group_3, blue: group_4}
        """
        # Extract group name and the content inside {}
        match = re.match(r"(\w+)\s*\{(.+)\}", expr)
        if not match:
            raise ValueError(f"Invalid region syntax: {expr}")

        main_group_name = match.group(1)
        color_content = match.group(2)

        # Parse color mappings: "red: group_2 x group_3, blue: group_4"
        color_coded_selections = {}

        # Split by comma to get each color mapping
        color_parts = []
        current_part = []
        depth = 0

        for char in color_content:
            if char == "," and depth == 0:
                color_parts.append("".join(current_part).strip())
                current_part = []
            else:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                current_part.append(char)

        if current_part:
            color_parts.append("".join(current_part).strip())

        # Parse each color mapping
        for color_part in color_parts:
            if ":" not in color_part:
                raise ValueError(f"Invalid color mapping (missing ':'): {color_part}")

            color, groups_str = color_part.split(":", 1)
            color = color.strip()
            groups_str = groups_str.strip()

            # Parse the groups for this color (recursively)
            color_selections = self._parse_groups(groups_str)
            color_coded_selections[color] = color_selections

        return GroupSelection(
            group_code_name=main_group_name,
            include_only=None,
            exclude=None,
            is_regioned=True,
            region_group_selections=color_coded_selections,
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

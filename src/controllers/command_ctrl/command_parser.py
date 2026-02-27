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
    merged_groups: Optional[list["GroupSelection"]] = None
    is_zipped: bool = False
    zipped_groups: Optional[list["GroupSelection"]] = None
    is_regioned: bool = False
    region_group_selections: Optional[dict[str, list["GroupSelection"]]] = None
    is_template: bool = False
    template_group_selections: Optional[dict[str, list["GroupSelection"]]] = None

    def to_dict(self):
        result = {
            "group_code_name": self.group_code_name,
            "include_only": self.include_only,
            "exclude": list(self.exclude) if self.exclude else None,
        }
        if self.is_merged:
            result["is_merged"] = True
            assert self.merged_groups
            result["merged_groups"] = [gs.to_dict() for gs in self.merged_groups]
        if self.is_zipped:
            result["is_zipped"] = True
            assert self.zipped_groups
            result["zipped_groups"] = [gs.to_dict() for gs in self.zipped_groups]
        if self.is_regioned:
            assert self.region_group_selections
            result["is_regioned"] = True
            result["region_group_selections"] = {
                region: [gs.to_dict() for gs in selections]
                for region, selections in self.region_group_selections.items()
            }
        if self.is_template:
            assert self.template_group_selections
            result["is_template"] = True
            result["template_group_selections"] = {
                template: [gs.to_dict() for gs in selections]
                for template, selections in self.template_group_selections.items()
            }
        return result


def dict_to_group_selection(data: dict) -> "GroupSelection":
    """Convert dictionary to GroupSelection dataclass"""

    merged_groups = None
    if data.get("is_merged") and data.get("merged_groups"):
        merged_groups = [dict_to_group_selection(s) for s in data["merged_groups"]]

    zipped_groups = None
    if data.get("is_zipped") and data.get("zipped_groups"):
        zipped_groups = [dict_to_group_selection(s) for s in data["zipped_groups"]]

    # Handle region_group_selections - recursive conversion
    color_coded = None
    if data.get("is_regioned") and data.get("region_group_selections"):
        color_coded = {}
        for color, selections_list in data["region_group_selections"].items():
            color_coded[color] = [dict_to_group_selection(s) for s in selections_list]

    # Handle template_group_selections - recursive conversion
    templates = None
    if data.get("is_template") and data.get("template_group_selections"):
        templates = {}
        for template, selections_list in data["template_group_selections"].items():
            templates[template] = [dict_to_group_selection(s) for s in selections_list]

    return GroupSelection(
        group_code_name=data["group_code_name"],
        include_only=data.get("include_only"),
        exclude=set(data["exclude"]) if data.get("exclude") else None,
        is_merged=data.get("is_merged", False),
        merged_groups=merged_groups,
        is_zipped=data.get("is_zipped", False),
        zipped_groups=zipped_groups,
        is_regioned=data.get("is_regioned", False),
        region_group_selections=color_coded,
        is_template=data.get("is_template", False),
        template_group_selections=templates,
    )


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

    def _contains_at_top_level(self, expr: str, token: str) -> bool:
        """Check if token exists in expr outside of any braces or brackets"""
        depth_braces = 0
        depth_brackets = 0
        i = 0
        while i < len(expr):
            if expr[i] == "{":
                depth_braces += 1
            elif expr[i] == "}":
                depth_braces -= 1
            elif expr[i] == "[":
                depth_brackets += 1
            elif expr[i] == "]":
                depth_brackets -= 1
            elif depth_braces == 0 and depth_brackets == 0:
                if expr[i : i + len(token)] == token:
                    return True
            i += 1
        return False

    def _parse_groups(self, groups_part: str) -> list[GroupSelection]:
        group_expressions = []
        current = []
        depth_braces = 0
        depth_brackets = 0

        i = 0
        while i < len(groups_part):
            char = groups_part[i]

            if char == "{":
                depth_braces += 1
                current.append(char)
            elif char == "}":
                depth_braces -= 1
                current.append(char)
            elif char == "[":
                depth_brackets += 1
                current.append(char)
            elif char == "]":
                depth_brackets -= 1
                current.append(char)
            elif (
                char == " "
                and i + 2 < len(groups_part)
                and groups_part[i : i + 3] == " * "
                and depth_braces == 0
                and depth_brackets == 0
            ):
                group_expressions.append("".join(current).strip())
                current = []
                i += 2
            else:
                current.append(char)

            i += 1

        if current:
            group_expressions.append("".join(current).strip())

        selections = []
        for expr in group_expressions:
            if self._contains_at_top_level(expr, " && "):
                selection = self._parse_merged_groups(expr)
            elif self._contains_at_top_level(expr, " || "):
                selection = self._parse_zipped_groups(expr)
            elif "[" in expr:
                selection = self._parse_group_with_templates(expr)
            elif "{" in expr:
                selection = self._parse_region_groups(expr)
            else:
                selection = self._parse_group_expression(expr)
            selections.append(selection)

        return selections

    def _parse_merged_groups(self, expr: str) -> GroupSelection:
        group_parts = []
        current_part = []
        depth_brackets = 0
        depth_braces = 0

        i = 0
        while i < len(expr):
            char = expr[i]

            if char == "[":
                depth_brackets += 1
                current_part.append(char)
            elif char == "]":
                depth_brackets -= 1
                current_part.append(char)
            elif char == "{":
                depth_braces += 1
                current_part.append(char)
            elif char == "}":
                depth_braces -= 1
                current_part.append(char)
            elif (
                char == " "
                and i + 4 <= len(expr)
                and expr[i : i + 4] == " && "
                and depth_brackets == 0
                and depth_braces == 0
            ):
                group_parts.append("".join(current_part).strip())
                current_part = []
                i += 3
            else:
                current_part.append(char)

            i += 1

        if current_part:
            group_parts.append("".join(current_part).strip())

        merged_groups: list[GroupSelection] = []
        all_group_names = []

        for part in group_parts:
            if "[" in part:
                selection = self._parse_group_with_templates(part)
            elif "{" in part:
                selection = self._parse_region_groups(part)
            else:
                selection = self._parse_group_expression(part)
            merged_groups.append(selection)
            all_group_names.append(selection.group_code_name)

        return GroupSelection(
            group_code_name="+".join(all_group_names),
            include_only=None,
            exclude=None,
            is_merged=True,
            merged_groups=merged_groups,
        )

    def _parse_zipped_groups(self, expr: str) -> GroupSelection:
        group_parts = []
        current_part = []
        depth_brackets = 0
        depth_braces = 0

        i = 0
        while i < len(expr):
            char = expr[i]

            if char == "[":
                depth_brackets += 1
                current_part.append(char)
            elif char == "]":
                depth_brackets -= 1
                current_part.append(char)
            elif char == "{":
                depth_braces += 1
                current_part.append(char)
            elif char == "}":
                depth_braces -= 1
                current_part.append(char)
            elif (
                char == " "
                and i + 4 <= len(expr)
                and expr[i : i + 4] == " || "
                and depth_brackets == 0
                and depth_braces == 0
            ):
                group_parts.append("".join(current_part).strip())
                current_part = []
                i += 3
            else:
                current_part.append(char)

            i += 1

        if current_part:
            group_parts.append("".join(current_part).strip())

        zipped_groups: list[GroupSelection] = []
        all_group_names = []

        for part in group_parts:
            if "[" in part:
                selection = self._parse_group_with_templates(part)
            elif "{" in part:
                selection = self._parse_region_groups(part)
            else:
                selection = self._parse_group_expression(part)
            zipped_groups.append(selection)
            all_group_names.append(selection.group_code_name)

        return GroupSelection(
            group_code_name="|".join(all_group_names),
            include_only=None,
            exclude=None,
            is_zipped=True,
            zipped_groups=zipped_groups,
        )

    def _parse_region_groups(self, expr: str) -> GroupSelection:
        """
        Parse region groups expression like:
        - group_1{red: group_2 * group_3, blue: group_4}
        """
        # Extract group name and the content inside {}
        match = re.match(r"(\w+)\s*\{(.+)\}", expr)
        if not match:
            raise ValueError(f"Invalid region syntax: {expr}")

        main_group_name = match.group(1)
        color_content = match.group(2)

        # Parse color mappings: "red: group_2 * group_3, blue: group_4"
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

    def _parse_group_with_templates(self, expr: str) -> GroupSelection:
        bracket_start = expr.find("[")
        if bracket_start == -1:
            raise ValueError(f"No template brackets found: {expr}")

        main_part = expr[:bracket_start].strip()

        base_match = re.match(r"(\w+)", main_part)
        if not base_match:
            raise ValueError(f"Invalid template group syntax: {expr}")

        group_name = base_match.group(1)
        include_items = None
        exclude_items = set()

        paren_match = re.search(r"\(([^)]+)\)", main_part)
        if paren_match:
            paren_content = paren_match.group(1)
            items = [item.strip() for item in paren_content.split(",")]

            if items and items[0].startswith("~"):
                exclude_items.update(item.lstrip("~") for item in items)
            else:
                include_items = items

        bracket_match = re.search(r"\[([^\]]+)\]", expr)
        if not bracket_match:
            raise ValueError(f"No template brackets found: {expr}")

        template_content = bracket_match.group(1)
        template_selections = {}

        # Find all template mappings by looking for pattern: word:
        # This handles "red: group_2(3) && group_7, blue: group_6"
        template_pattern = r"(\w+):\s*"
        matches = list(re.finditer(template_pattern, template_content))

        for i, match in enumerate(matches):
            template_name = match.group(1)
            start = match.end()

            # Find where this template's content ends (next template name or end of string)
            if i + 1 < len(matches):
                end = matches[i + 1].start()
                groups_str = template_content[start:end].rstrip(", ").strip()
            else:
                groups_str = template_content[start:].strip()

            # Parse the groups for this template
            template_group_selections = self._parse_groups(groups_str)
            template_selections[template_name] = template_group_selections

        return GroupSelection(
            group_code_name=group_name,
            include_only=include_items,
            exclude=exclude_items if exclude_items else None,
            is_template=True,
            template_group_selections=template_selections,
        )

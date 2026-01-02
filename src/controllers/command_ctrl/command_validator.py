from dataclasses import dataclass

from src.controllers.command_ctrl.command_parser import ParsedCommand
from src.db.records import GroupRecord, ItemRecord, ServerRecord, WorkflowRecord


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]


async def validate_code_names(cmd: ParsedCommand) -> ValidationResult:
    errors = []

    # Validate server
    server_exists = await ServerRecord.filter(code_name=cmd.server_code_name).exists()
    if not server_exists:
        errors.append(f"Server '{cmd.server_code_name}' not found")

    # Validate workflow
    workflow_exists = await WorkflowRecord.filter(
        code_name=cmd.workflow_code_name
    ).exists()
    if not workflow_exists:
        errors.append(f"Workflow '{cmd.workflow_code_name}' not found")

    # Validate groups and items
    for group_sel in cmd.group_selections:
        # Handle merged groups
        if group_sel.is_merged:
            assert group_sel.merged_groups is not None
            for merged_group in group_sel.merged_groups:
                group_code = merged_group["group_code_name"]

                # Check group exists
                group = await GroupRecord.filter(code_name=group_code).first()
                if not group:
                    errors.append(f"Group '{group_code}' not found")
                    continue

                # Check included items
                if merged_group["include_only"]:
                    for item_code in merged_group["include_only"]:
                        item_exists = await ItemRecord.filter(
                            group_id=group.id, code_name=item_code
                        ).exists()
                        if not item_exists:
                            errors.append(
                                f"Item '{item_code}' not found in group '{group_code}'"
                            )

                # Check excluded items
                if merged_group["exclude"]:
                    for item_code in merged_group["exclude"]:
                        item_exists = await ItemRecord.filter(
                            group_id=group.id, code_name=item_code
                        ).exists()
                        if not item_exists:
                            errors.append(
                                f"Item '{item_code}' not found in group '{group_code}'"
                            )
        else:
            # Handle single group
            group_code = group_sel.group_code_name

            # Check group exists
            group = await GroupRecord.filter(code_name=group_code).first()
            if not group:
                errors.append(f"Group '{group_code}' not found")
                continue

            # Check included items
            if group_sel.include_only:
                for item_code in group_sel.include_only:
                    item_exists = await ItemRecord.filter(
                        group_id=group.id, code_name=item_code
                    ).exists()
                    if not item_exists:
                        errors.append(
                            f"Item '{item_code}' not found in group '{group_code}'"
                        )

            # Check excluded items
            if group_sel.exclude:
                for item_code in group_sel.exclude:
                    item_exists = await ItemRecord.filter(
                        group_id=group.id, code_name=item_code
                    ).exists()
                    if not item_exists:
                        errors.append(
                            f"Item '{item_code}' not found in group '{group_code}'"
                        )

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)

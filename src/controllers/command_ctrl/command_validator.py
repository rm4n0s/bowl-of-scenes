from dataclasses import dataclass

from src.controllers.command_ctrl.command_parser import GroupSelection, ParsedCommand
from src.db.records import GeneratorRecord, GroupRecord, ItemRecord, ServerRecord
from src.db.records.fixer_rec import FixerRecord
from src.db.records.item_rec import ColorCodeImages


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
    generator_exists = await GeneratorRecord.filter(
        code_name=cmd.generator_code_name
    ).exists()
    if not generator_exists:
        errors.append(f"Workflow '{cmd.generator_code_name}' not found")

    if cmd.fixers:
        for fixer_cn in cmd.fixers:
            fixer_exists = await FixerRecord.filter(code_name=fixer_cn).exists()
            if not fixer_exists:
                errors.append(f"Fixer '{fixer_cn}' not found")

    # Validate groups and items
    gr_errors = await validate_group_selections(cmd.group_selections)

    cc_errors = await validate_color_coded(cmd.group_selections)

    errors.extend(gr_errors)
    errors.extend(cc_errors)
    return ValidationResult(is_valid=len(errors) == 0, errors=errors)


async def validate_color_coded(group_selections: list[GroupSelection]) -> list[str]:
    errors = []
    color_coded_count = 0
    for gs in group_selections:
        if not gs.is_color_coded:
            continue

        color_coded_count += 1
        if gs.color_coded_group_selections is None:
            errors.append(
                f"color_coded_group_selections was empty for '{gs.group_code_name}'"
            )
            continue

        group = await GroupRecord.get_or_none(code_name=gs.group_code_name)
        if group is None:
            errors.append(f"Group '{gs.group_code_name}' not found")
            continue

        masked_items = await ItemRecord.filter(group_id=group.id).all()
        keywords_from_group = set()
        for mi in masked_items:
            ccis_dict = mi.color_coded_images
            if ccis_dict is None:
                continue

            ccis = ColorCodeImages(**ccis_dict)
            keywords_from_group.update(ccis.mask_files.keys())

        keywords_from_command = set(gs.color_coded_group_selections.keys())
        if keywords_from_group != keywords_from_command:
            missing_in_command = keywords_from_group - keywords_from_command
            missing_in_items = keywords_from_command - keywords_from_group

            if len(missing_in_command) > 0:
                errors.append(
                    f"Missing color coded keywords from command: {missing_in_command}"
                )

            if len(missing_in_items) > 0:
                errors.append(
                    f"Missing color coded keywords from group '{gs.group_code_name}': {missing_in_items}'"
                )

    if color_coded_count > 1:
        errors.append("You can use only one color coded group in the command")

    return errors


async def validate_group_selections(
    group_selections: list[GroupSelection],
) -> list[str]:
    errors = []
    for group_sel in group_selections:
        if group_sel.is_color_coded:
            continue

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

    return errors

import os
from dataclasses import dataclass
from itertools import product
from typing import Any

from tortoise.expressions import F

from src.controllers.command_ctrl.command_parser import (
    GroupSelection,
    PromptLanguageParser,
)
from src.controllers.command_ctrl.command_validator import (
    validate_code_names,
)
from src.controllers.manager_ctrl import Manager
from src.core.config import Config
from src.db.records import (
    CommandRecord,
    GeneratorRecord,
    GroupRecord,
    ItemRecord,
    JobRecord,
    ServerRecord,
)
from src.db.records.fixer_rec import FixerRecord
from src.db.records.item_rec import ColorCodeImages
from src.db.records.job_rec import ColorCodedPrompt


@dataclass
class CommandInput:
    project_id: int
    code: str


@dataclass
class CommandOutput:
    id: int
    project_id: int
    order: int
    command_code: str
    command_json: dict[str, Any]


async def get_items_per_group_without_color_code(
    group_selections: list[GroupSelection],
) -> list[list[ItemRecord]]:
    items_per_group: list[list[ItemRecord]] = []
    for group_sel in group_selections:
        if group_sel.is_color_coded:
            continue

        # Handle merged groups
        if group_sel.is_merged:
            merged_items: list[ItemRecord] = []
            assert group_sel.merged_groups is not None
            for merged_group in group_sel.merged_groups:
                group_code = merged_group["group_code_name"]

                # Check group exists
                group = await GroupRecord.filter(code_name=group_code).first()
                if not group:
                    raise ValueError(f"Group '{group_code}' not found")

                items = []
                if (
                    merged_group["exclude"] is None
                    and merged_group["include_only"] is None
                ):
                    items = await ItemRecord.filter(group_id=group.id).all()

                elif merged_group["exclude"] is not None:
                    items = (
                        await ItemRecord.filter(group_id=group.id)
                        .exclude(code_name__in=merged_group["exclude"])
                        .all()
                    )

                elif merged_group["include_only"] is not None:
                    items = await ItemRecord.filter(
                        group_id=group.id, code_name__in=merged_group["include_only"]
                    ).all()

                merged_items.extend(items)

            items_per_group.append(merged_items)
        else:
            # Handle single group
            group_code = group_sel.group_code_name

            # Check group exists
            group = await GroupRecord.filter(code_name=group_code).first()
            if not group:
                raise ValueError(f"Group '{group_code}' not found")

            items = []
            if group_sel.exclude is None and group_sel.include_only is None:
                items = await ItemRecord.filter(group_id=group.id).all()

            elif group_sel.exclude is not None:
                items = (
                    await ItemRecord.filter(group_id=group.id)
                    .exclude(code_name__in=group_sel.exclude)
                    .all()
                )

            elif group_sel.include_only is not None:
                items = await ItemRecord.filter(
                    group_id=group.id, code_name__in=group_sel.include_only
                ).all()

            items_per_group.append(items)

    return items_per_group


async def get_color_coded_prompt_comb(
    group_selections: list[GroupSelection],
) -> dict[str, list[ColorCodedPrompt]] | None:
    res = None
    for gs in group_selections:
        if not gs.is_color_coded:
            continue

        assert gs.color_coded_group_selections is not None
        group = await GroupRecord.get_or_none(code_name=gs.group_code_name)
        if group is None:
            continue

        masked_items = await ItemRecord.filter(group_id=group.id).all()
        color_coded_prompts_per_key: dict[str, list[ColorCodedPrompt]] = {}

        for mi in masked_items:
            ccis_dict = mi.color_coded_images
            assert ccis_dict is not None
            ccis = ColorCodeImages(**ccis_dict)
            for keyword, mask_file in ccis.mask_files.items():
                group_sels = gs.color_coded_group_selections[keyword]

                items_per_group = await get_items_per_group_without_color_code(
                    group_sels
                )
                combined_items = [list(combo) for combo in product(*items_per_group)]
                color_coded_prompts_per_key[keyword] = []
                for items in combined_items:
                    prompt_positive = ""
                    for item in items:
                        if len(item.positive_prompt) > 0:
                            prompt_positive += item.positive_prompt + ", "

                    ccp = ColorCodedPrompt(
                        keyword=keyword,
                        mask_file=os.path.abspath(mask_file),
                        prompt=prompt_positive,
                    )
                    color_coded_prompts_per_key[keyword].append(ccp)

        res = color_coded_prompts_per_key
    return res


async def create_jobs(conf: Config, command: CommandRecord) -> list[JobRecord]:
    parser = PromptLanguageParser()
    cmd = parser.parse(command.command_code)
    server = await ServerRecord.filter(code_name=cmd.server_code_name).first()
    if server is None:
        raise ValueError(f"Server '{cmd.server_code_name}' not found")

    generator = await GeneratorRecord.filter(code_name=cmd.generator_code_name).first()
    if generator is None:
        raise ValueError(f"Generator '{cmd.generator_code_name}' not found")

    fixers: list[FixerRecord] = []
    if cmd.fixers:
        for v in cmd.fixers:
            fix_rec = await FixerRecord.filter(code_name=v).first()
            if fix_rec is None:
                raise ValueError(f"Fixer '{v}' not found")

            fixers.append(fix_rec)

    items_per_group = await get_items_per_group_without_color_code(cmd.group_selections)
    combined_items = [list(combo) for combo in product(*items_per_group)]

    ccp_comb = await get_color_coded_prompt_comb(cmd.group_selections)
    ccp_list = []
    if ccp_comb is not None:
        keys = list(ccp_comb.keys())
        values_lists = list(ccp_comb.values())
        ccp_list = [dict(zip(keys, combo)) for combo in product(*values_lists)]

    print(f"Will run {len(combined_items)}")
    res: list[JobRecord] = []
    for items in combined_items:
        prompt_positive = ""
        prompt_negative = ""
        reference_controlnet_img = None
        reference_ipadapter_img = None
        lora_list = []

        group_item_id_list = []
        result_filename_img = f"{server.code_name}_{generator.code_name}_{command.id}"
        for item in items:
            group = await GroupRecord.get_or_none(id=item.group_id)
            if group is not None:
                result_filename_img += "_" + group.code_name

            result_filename_img += "_" + item.code_name
            group_item_id_list.append(
                {
                    "group_id": item.group_id,
                    "item_id": item.id,
                }
            )
            if len(item.positive_prompt) > 0:
                prompt_positive += item.positive_prompt + ", "
            if len(item.negative_prompt) > 0:
                prompt_negative += item.negative_prompt + ", "
            if item.controlnet_reference_image is not None:
                reference_controlnet_img = os.path.abspath(
                    item.controlnet_reference_image
                )

            if item.ipadapter_reference_image is not None:
                reference_ipadapter_img = os.path.abspath(
                    item.ipadapter_reference_image
                )

            if item.lora is not None:
                lora_list.append(item.lora)

        if len(ccp_list) > 0:
            for i, ccp in enumerate(ccp_list):
                result_img = os.path.join(
                    conf.result_path, result_filename_img + f"ccp_{i}" + ".png"
                )
                job = await JobRecord.create(
                    project_id=command.project_id,
                    command_id=command.id,
                    group_item_id_list=group_item_id_list,
                    code_str=command.command_code,
                    server_code_name=server.code_name,
                    server_host=server.host,
                    generator_code_name=generator.code_name,
                    prompt_positive=prompt_positive,
                    prompt_negative=prompt_negative,
                    color_coded_prompts=ccp,
                    reference_controlnet_img=reference_controlnet_img,
                    reference_ipadapter_img=reference_ipadapter_img,
                    lora_list=lora_list,
                    result_img=result_img,
                )
                res.append(job)
        else:
            result_img = os.path.join(conf.result_path, result_filename_img + ".png")
            job = await JobRecord.create(
                project_id=command.project_id,
                command_id=command.id,
                group_item_id_list=group_item_id_list,
                code_str=command.command_code,
                server_code_name=server.code_name,
                server_host=server.host,
                generator_code_name=generator.code_name,
                prompt_positive=prompt_positive,
                prompt_negative=prompt_negative,
                reference_controlnet_img=reference_controlnet_img,
                reference_ipadapter_img=reference_ipadapter_img,
                lora_list=lora_list,
                result_img=result_img,
            )
            res.append(job)

    if len(fixers) > 0:
        process_jobs = res.copy()
        for fixer in fixers:
            new_process_jobs = []
            for pj in process_jobs:
                result_filename_img = os.path.basename(pj.result_img)
                result_img = os.path.join(
                    conf.result_path, fixer.code_name + "_" + result_filename_img
                )

                job = await JobRecord.create(
                    project_id=command.project_id,
                    command_id=command.id,
                    group_item_id_list=pj.group_item_id_list,
                    code_str=command.command_code,
                    server_code_name=server.code_name,
                    server_host=server.host,
                    fixer_code_name=fixer.code_name,
                    fix_job_id=pj.id,
                    generator_code_name=None,
                    prompt_positive="",
                    prompt_negative="",
                    reference_controlnet_img=None,
                    reference_ipadapter_img=None,
                    lora_list=None,
                    result_img=result_img,
                )
                res.append(job)
                new_process_jobs.append(job)

            process_jobs = new_process_jobs.copy()

    return res


async def run_command(manager: Manager, command_id: int):
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    await manager.add_command(cmd.id)


async def recreate_command(conf: Config, command_id: int):
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    await delete_jobs_from_command(command_id)

    await create_jobs(conf, cmd)


async def get_command(command_id: int) -> CommandOutput:
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    return CommandOutput(
        id=cmd.id,
        project_id=cmd.project_id,
        order=cmd.order,
        command_code=cmd.command_code,
        command_json=cmd.command_json,
    )


async def add_command(
    conf: Config, input: CommandInput, insert_at: int | None = None
) -> list[str] | None:
    """
    Add a new command. If insert_at is specified, insert at that position,
    otherwise append to the end.
    """
    if insert_at is None:
        # Append to end
        last_command = (
            await CommandRecord.filter(project_id=input.project_id)
            .order_by("-order")
            .first()
        )

        next_order = (last_command.order + 1) if last_command else 1
    else:
        # Insert at specific position - shift everything after it
        await CommandRecord.filter(
            project_id=input.project_id, order__gte=insert_at
        ).update(order=F("order") + 1)

        next_order = insert_at

    parser = PromptLanguageParser()
    command = parser.parse(input.code)
    valid_res = await validate_code_names(command)
    if not valid_res.is_valid:
        return valid_res.errors

    print("command_json", command)
    cmd_rec = await CommandRecord.create(
        project_id=input.project_id,
        order=next_order,
        command_code=input.code,
        command_json=command.to_dict(),
    )

    await create_jobs(conf, cmd_rec)


async def edit_command(conf: Config, id: int, input: CommandInput) -> list[str] | None:
    cmd = await CommandRecord.get_or_none(id=id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    if cmd.command_code != input.code:
        parser = PromptLanguageParser()
        command = parser.parse(input.code)
        valid_res = await validate_code_names(command)
        if not valid_res.is_valid:
            return valid_res.errors

        print("command_json", command)
        cmd.command_code = input.code
        cmd.command_json = command.to_dict()
        await cmd.save()
        await delete_jobs_from_command(cmd.id)
        await create_jobs(conf, cmd)


async def delete_jobs_from_command(command_id: int):
    jobs = await JobRecord.filter(command_id=command_id).all()
    for job in jobs:
        if job.result_img is not None:
            if os.path.exists(job.result_img):
                os.remove(job.result_img)

        await job.delete()


async def delete_command(command_id: int):
    """
    Delete a command and adjust the order of remaining commands.
    """
    command = await CommandRecord.get(id=command_id)
    project_id = command.project_id
    order = command.order
    await delete_jobs_from_command(command_id)
    await command.delete()

    # Shift down all commands after the deleted one
    await CommandRecord.filter(project_id=project_id, order__gt=order).update(
        order=F("order") - 1
    )


async def move_command(command_id: int, new_order: int) -> CommandOutput | None:
    """
    Move a command to a new position and reorder others accordingly.
    """
    command = await CommandRecord.get(id=command_id)
    old_order = command.order
    project_id = command.project_id

    if old_order == new_order:
        return None  # No change needed

    if old_order < new_order:
        # Moving down: shift commands between old and new position up
        await CommandRecord.filter(
            project_id=project_id, order__gt=old_order, order__lte=new_order
        ).update(order=F("order") - 1)
    else:
        # Moving up: shift commands between new and old position down
        await CommandRecord.filter(
            project_id=project_id, order__gte=new_order, order__lt=old_order
        ).update(order=F("order") + 1)

    command.order = new_order
    await command.save()

    return CommandOutput(
        id=command.id,
        project_id=command.project_id,
        order=command.order,
        command_code=command.command_code,
        command_json=command.command_json,
    )


async def increment_order(command_id: int) -> CommandOutput | None:
    """
    Move a command down by one position (increase order).
    """
    command = await CommandRecord.get(id=command_id)

    # Get the max order for this project
    max_command = (
        await CommandRecord.filter(project_id=command.project_id)
        .order_by("-order")
        .first()
    )
    assert max_command is not None

    if command.order >= max_command.order:
        return None  # Already at the end

    return await move_command(command_id, command.order + 1)


async def decrement_order(command_id: int) -> CommandOutput | None:
    """
    Move a command up by one position (decrease order).
    """
    command = await CommandRecord.get(id=command_id)

    if command.order <= 1:
        return None  # Already at the beginning

    return await move_command(command_id, command.order - 1)


async def reorder_project_commands(project_id: int):
    """
    Rebuild the order sequence to ensure it's 1, 2, 3, 4...
    Useful if you suspect gaps or inconsistencies.
    """
    commands = await CommandRecord.filter(project_id=project_id).order_by("order").all()

    for index, command in enumerate(commands, start=1):
        if command.order != index:
            command.order = index
            await command.save()


async def list_commands(project_id: int) -> list[CommandOutput]:
    query = CommandRecord.filter(project_id=project_id).order_by("order")

    commands = await query.all()
    out = []
    for cmd in commands:
        out.append(
            CommandOutput(
                id=cmd.id,
                project_id=cmd.project_id,
                order=cmd.order,
                command_code=cmd.command_code,
                command_json=cmd.command_json,
            )
        )
    return out

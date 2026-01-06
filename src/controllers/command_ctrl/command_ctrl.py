import os
from dataclasses import dataclass
from itertools import product
from typing import Any

from tortoise.expressions import F

from src.controllers.command_ctrl.command_parser import (
    PromptLanguageParser,
)
from src.controllers.command_ctrl.command_validator import (
    validate_code_names,
)
from src.controllers.ctrl_types import serialize_job
from src.controllers.manager_ctrl import Manager
from src.core.config import Config
from src.db.records import (
    CommandRecord,
    GroupRecord,
    ItemRecord,
    JobRecord,
    ServerRecord,
    WorkflowRecord,
)


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


async def create_jobs(conf: Config, command: CommandRecord) -> list[JobRecord]:
    parser = PromptLanguageParser()
    cmd = parser.parse(command.command_code)
    server = await ServerRecord.filter(code_name=cmd.server_code_name).first()
    if server is None:
        raise ValueError(f"Server '{cmd.server_code_name}' not found")

    workflow = await WorkflowRecord.filter(code_name=cmd.workflow_code_name).first()
    if workflow is None:
        raise ValueError(f"Workflow '{cmd.workflow_code_name}' not found")

    items_per_group: list[list[ItemRecord]] = []
    for group_sel in cmd.group_selections:
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

    combined_items = [list(combo) for combo in product(*items_per_group)]
    print(f"Will run {len(combined_items)}")
    res = []
    for items in combined_items:
        prompt_positive = ""
        prompt_negative = ""
        reference_controlnet_img = None
        reference_ipadapter_img = None
        lora_list = []

        group_item_id_list = []
        result_filename_img = f"{server.code_name}_{workflow.code_name}_{command.id}"
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
                reference_controlnet_img = item.controlnet_reference_image

            if item.ipadapter_reference_image is not None:
                reference_ipadapter_img = item.ipadapter_reference_image

            if item.lora is not None:
                lora_list.append(item.lora)

        result_img = os.path.join(conf.result_path, result_filename_img + ".png")
        job = await JobRecord.create(
            project_id=command.project_id,
            command_id=command.id,
            group_item_id_list=group_item_id_list,
            code_str=command.command_code,
            server_code_name=server.code_name,
            server_host=server.host,
            workflow_code_name=workflow.code_name,
            prompt_positive=prompt_positive,
            prompt_negative=prompt_negative,
            reference_controlnet_img=reference_controlnet_img,
            reference_ipadapter_img=reference_ipadapter_img,
            lora_list=lora_list,
            result_img=result_img,
        )
        res.append(job)
    return res


async def run_command(manager: Manager, command_id: int):
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    jobs = await JobRecord.filter(command_id=command_id).all()
    for job in jobs:
        await manager.add_job(serialize_job(job))


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

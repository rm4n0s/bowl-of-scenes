import copy
import hashlib
import json
import os
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import aiofiles
from tortoise.expressions import F

from src.controllers.command_ctrl.command_parser import (
    GroupSelection,
    PromptLanguageParser,
)
from src.controllers.command_ctrl.command_validator import (
    validate_code_names,
)
from src.controllers.ctrl_types import (
    CommandInput,
    CommandOutput,
    CoordinatedRegion,
    CoordinatedRegionKeyword,
    JobStatus,
    MaskRegionImages,
    RegionPrompt,
)
from src.controllers.manager_ctrl import Manager
from src.controllers.serializers import serialize_command
from src.core.config import Config
from src.core.utils import utils
from src.core.utils.paginator import PaginatedOutput
from src.core.utils.zip import create_zip
from src.db.records import (
    CommandRecord,
    GeneratorRecord,
    GroupRecord,
    ItemRecord,
    JobRecord,
    ServerRecord,
)
from src.db.records.fixer_rec import FixerRecord


async def get_items_by_merged_groups(group_sel: GroupSelection) -> list[ItemRecord]:
    merged_items: list[ItemRecord] = []
    assert group_sel.merged_groups is not None

    for merged_group in group_sel.merged_groups:
        group_code = merged_group.group_code_name

        # Check group exists
        group = await GroupRecord.filter(code_name=group_code).first()
        if not group:
            raise ValueError(f"Group '{group_code}' not found")

        items = []
        if merged_group.exclude is None and merged_group.include_only is None:
            items = await ItemRecord.filter(group_id=group.id).all()

        elif merged_group.exclude is not None:
            items = (
                await ItemRecord.filter(group_id=group.id)
                .exclude(code_name__in=merged_group.exclude)
                .all()
            )

        elif merged_group.include_only is not None:
            items = await ItemRecord.filter(
                group_id=group.id, code_name__in=merged_group.include_only
            ).all()

        if merged_group.is_template:
            items = await get_template_prompt_comb(merged_group)

        merged_items.extend(items)

    return merged_items


async def get_items_by_zipped_groups(group_sel: GroupSelection) -> list[ItemRecord]:
    assert group_sel.zipped_groups is not None

    group_iteps_per_list: list[list[ItemRecord]] = []
    for zipped_group in group_sel.zipped_groups:
        group_code = zipped_group.group_code_name

        # Check group exists
        group = await GroupRecord.filter(code_name=group_code).first()
        if not group:
            raise ValueError(f"Group '{group_code}' not found")

        items: list[ItemRecord] = []
        if zipped_group.exclude is None and zipped_group.include_only is None:
            items = await ItemRecord.filter(group_id=group.id).all()

        elif zipped_group.exclude is not None:
            items = (
                await ItemRecord.filter(group_id=group.id)
                .exclude(code_name__in=zipped_group.exclude)
                .all()
            )

        elif zipped_group.include_only is not None:
            items = await ItemRecord.filter(
                group_id=group.id, code_name__in=zipped_group.include_only
            ).all()

        if zipped_group.is_template:
            items = await get_template_prompt_comb(zipped_group)

        group_iteps_per_list.append(items)

    combo_items_per_zip = [combo for combo in zip(*group_iteps_per_list)]
    zipped_items: list[ItemRecord] = []
    for combo in combo_items_per_zip:
        group_code_name = ""
        prompt_positive = ""
        prompt_negative = ""
        lora_list = []
        controlnet_list = []
        ipadapter = None

        for item in combo:
            group_code_name += item.code_name + ""
            if item.lora_list is not None:
                if len(item.lora_list) > 0:
                    lora_list.extend(item.lora_list)

            if item.controlnets is not None:
                if len(item.controlnets) > 0:
                    controlnet_list.extend(item.controlnet_list)

            if len(item.positive_prompt) > 0:
                prompt_positive += item.positive_prompt + " "

            if len(item.negative_prompt) > 0:
                prompt_negative += item.negative_prompt + " "

            if item.ipadapter is not None:
                ipadapter = item.ipadapter

        zipped_items.append(
            ItemRecord(
                code_name=group_code_name,
                positive_prompt=prompt_positive,
                negative_prompt=prompt_negative,
                lora_list=lora_list,
                ipadapter=ipadapter,
                controlnets=controlnet_list,
            )
        )

    return zipped_items


async def get_items_per_group_without_regioned_prompts(
    group_selections: list[GroupSelection],
) -> list[list[ItemRecord]]:
    items_per_group: list[list[ItemRecord]] = []
    for group_sel in group_selections:
        # Handle merged groups
        if group_sel.is_merged:
            assert group_sel.merged_groups is not None
            merged_items: list[ItemRecord] = await get_items_by_merged_groups(group_sel)
            items_per_group.append(merged_items)

        elif group_sel.is_zipped:
            assert group_sel.zipped_groups is not None
            zipped_items = await get_items_by_zipped_groups(group_sel)
            items_per_group.append(zipped_items)

        elif group_sel.is_template:
            items = await get_template_prompt_comb(group_sel)
            items_per_group.append(items)

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


async def get_template_prompt_comb(group_sel: GroupSelection) -> list[ItemRecord]:
    if not group_sel.is_template:
        return []

    assert group_sel.template_group_selections

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

    combined_per_key = {}
    for key, gs in group_sel.template_group_selections.items():
        combined_per_key[key] = []
        items_per_group = await get_items_per_group_without_regioned_prompts(gs)
        combined_items = [list(combo) for combo in product(*items_per_group)]

        for cis in combined_items:
            prompt_positive = ""
            prompt_negative = ""
            code_name = ""
            loras = []
            for ci in cis:
                code_name += ci.code_name
                if ci.lora_list is not None:
                    loras.extend(ci.lora_list)

                if len(ci.positive_prompt) > 0:
                    prompt_positive += ci.positive_prompt + " "

                if len(ci.negative_prompt) > 0:
                    prompt_negative += ci.negative_prompt + " "

            combined_per_key[key].append(
                {
                    "code_name": code_name,
                    "loras": loras,
                    "positive": prompt_positive,
                    "negative": prompt_negative,
                }
            )

    cartesianed = [
        dict(zip(combined_per_key.keys(), values))
        for values in product(*combined_per_key.values())
    ]

    res_items = {}
    for cart_index, cart_dict in enumerate(cartesianed):
        for item_index, item in enumerate(items):
            new_item = copy.copy(item)
            for key, val in cart_dict.items():
                if new_item.lora_list is None:
                    new_item.lora_list = []
                    exists = {}
                    for lora in val["loras"]:
                        if lora["name"] not in exists.keys():
                            new_item.lora_list.append(lora)
                            exists[lora["name"]] = True

                else:
                    ll = new_item.lora_list
                    ll.extend(val["loras"])
                    nlist = []
                    exists = {}
                    for lora in ll:
                        if lora["name"] not in exists.keys():
                            nlist.append(lora)
                            exists[lora["name"]] = True
                    new_item.lora_list = nlist

                tmpl_tags = utils.list_template_tags(new_item.positive_prompt)
                if key in tmpl_tags:
                    new_item.positive_prompt = utils.replace_template_tags(
                        new_item.positive_prompt, {key: val["positive"]}
                    )

                tmpl_tags = utils.list_template_tags(new_item.negative_prompt)
                if key in tmpl_tags:
                    new_item.negative_prompt = utils.replace_template_tags(
                        new_item.negative_prompt, {key: val["negative"]}
                    )

                new_item.code_name += (
                    str(cart_index) + str(item_index) + key + val["code_name"]
                )

            hashinput = new_item.positive_prompt + new_item.negative_prompt

            res_items[hashlib.sha256(hashinput.encode()).hexdigest()] = new_item

    return list(res_items.values())


@dataclass
class RegionPromptCombOutput:
    region_items: list[ItemRecord]
    regioned_prompts: list[dict[str, RegionPrompt]]


async def get_region_prompt_comb(
    group_selections: list[GroupSelection],
) -> RegionPromptCombOutput | None:
    the_group = None
    the_gs = None
    for gs in group_selections:
        if not gs.is_regioned:
            continue

        the_gs = gs
        group = await GroupRecord.get_or_none(code_name=gs.group_code_name)
        if group is None:
            continue
        the_group = group
        break

    if the_gs is None or the_group is None:
        return None

    assert the_gs.region_group_selections is not None

    region_items = await ItemRecord.filter(group_id=the_group.id).all()
    region_prompts_per_key: dict[str, list[RegionPrompt]] = {}

    for ri in region_items:
        if ri.mask_region_images is not None:
            mri = MaskRegionImages(**ri.mask_region_images)
            for keyword, mask_file in mri.mask_files.items():
                group_sels = the_gs.region_group_selections[keyword]

                items_per_group = await get_items_per_group_without_regioned_prompts(
                    group_sels
                )
                combined_items = [list(combo) for combo in product(*items_per_group)]
                region_prompts_per_key[keyword] = []
                for items in combined_items:
                    prompt_positive = ""
                    loras = []
                    for item in items:
                        if item.lora_list is not None:
                            loras.extend(item.lora_list)

                        if len(item.positive_prompt) > 0:
                            prompt_positive += item.positive_prompt + " "

                    rp = RegionPrompt(
                        keyword=keyword,
                        mask_file=os.path.abspath(mask_file),
                        coordinates=None,
                        prompt=prompt_positive,
                        loras=loras,
                    )
                    region_prompts_per_key[keyword].append(rp)
        elif ri.coordinated_regions is not None:
            crns = [CoordinatedRegionKeyword(**v) for v in ri.coordinated_regions]
            for crn in crns:
                group_sels = the_gs.region_group_selections[crn.keyword]
                items_per_group = await get_items_per_group_without_regioned_prompts(
                    group_sels
                )
                combined_items = [list(combo) for combo in product(*items_per_group)]
                region_prompts_per_key[crn.keyword] = []
                for items in combined_items:
                    prompt_positive = ""
                    loras = []
                    for item in items:
                        if item.lora_list is not None:
                            loras.extend(item.lora_list)

                        if len(item.positive_prompt) > 0:
                            prompt_positive += item.positive_prompt + " "

                    rp = RegionPrompt(
                        keyword=crn.keyword,
                        mask_file=None,
                        coordinates=CoordinatedRegion(
                            width=crn.width, height=crn.height, x=crn.x, y=crn.y
                        ),
                        loras=loras,
                        prompt=prompt_positive,
                    )
                    region_prompts_per_key[crn.keyword].append(rp)

    if len(region_prompts_per_key) == 0:
        return None

    keys = list(region_prompts_per_key.keys())
    values_lists = list(region_prompts_per_key.values())
    regioned_prompts = [dict(zip(keys, combo)) for combo in product(*values_lists)]

    return RegionPromptCombOutput(
        region_items=region_items,
        regioned_prompts=regioned_prompts,
    )


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

    items_per_group = await get_items_per_group_without_regioned_prompts(
        cmd.group_selections
    )
    combined_items = [list(combo) for combo in product(*items_per_group)]

    ccp_comb = await get_region_prompt_comb(cmd.group_selections)

    print(f"Will run {len(combined_items)}")
    res: list[JobRecord] = []
    output_type = generator.output_type
    output_type_attributes = generator.output_attributes
    for items in combined_items:
        prompt_positive = ""
        prompt_negative = ""
        lora_list = []
        controlnet_list = []
        ipadapter_list = []
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
                prompt_positive += item.positive_prompt + " "
            if len(item.negative_prompt) > 0:
                prompt_negative += item.negative_prompt + " "

            if item.ipadapter is not None:
                ipadapter_list.append(item.ipadapter)

            if item.lora_list is not None:
                lora_list.extend(item.lora_list)

            if item.controlnets is not None:
                controlnet_list.extend(item.controlnets)

            if item.output_type is not None and item.output_type_attributes is not None:
                output_type = item.output_type
                output_type_attributes = item.output_type_attributes

        prompt_positive = utils.remove_template_tags(prompt_positive)
        prompt_negative = utils.remove_template_tags(prompt_negative)
        file_type = ""
        if "file_type" in output_type_attributes.keys():
            file_type = output_type_attributes["file_type"]

        if ccp_comb is not None:
            for i, ccp in enumerate(ccp_comb.regioned_prompts):
                result_img = os.path.join(
                    conf.result_path,
                    result_filename_img + f"_ccp_{i}." + file_type,
                )
                for rc in ccp.values():
                    lora_list.extend(rc.loras)

                job = await JobRecord.create(
                    project_id=command.project_id,
                    command_id=command.id,
                    group_item_id_list=group_item_id_list,
                    code_str=command.command_code,
                    server_code_name=server.code_name,
                    server_host=server.host,
                    generator_code_name=generator.code_name,
                    generator_output_type=output_type,
                    generator_output_attributes=output_type_attributes,
                    prompt_positive=prompt_positive,
                    prompt_negative=prompt_negative,
                    region_prompts=ccp,
                    ipadapter_list=ipadapter_list,
                    controlnets=controlnet_list,
                    lora_list=lora_list,
                    result_img=result_img,
                    total_fixers=[fix.id for fix in fixers],
                )
                res.append(job)
        else:
            result_img = os.path.join(
                conf.result_path, result_filename_img + "." + file_type
            )
            job = await JobRecord.create(
                project_id=command.project_id,
                command_id=command.id,
                group_item_id_list=group_item_id_list,
                code_str=command.command_code,
                server_code_name=server.code_name,
                server_host=server.host,
                generator_code_name=generator.code_name,
                generator_output_type=output_type,
                generator_output_attributes=output_type_attributes,
                prompt_positive=prompt_positive,
                prompt_negative=prompt_negative,
                ipadapter_list=ipadapter_list,
                controlnets=controlnet_list,
                lora_list=lora_list,
                result_img=result_img,
                total_fixers=[fix.id for fix in fixers],
            )
            res.append(job)

    if len(res) > 0:
        last_job = res[len(res) - 1]
        last_job.is_last = True
        await last_job.save()

    return res


async def run_command(manager: Manager, command_id: int):
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    await JobRecord.filter(command_id=command_id, status=JobStatus.IDLE).update(
        status=JobStatus.QUEUED
    )

    cmd.status = JobStatus.QUEUED
    await cmd.save()

    await manager.add_command(cmd.id)


async def stop_command(command_id: int):
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    await JobRecord.filter(command_id=command_id, status=JobStatus.QUEUED).update(
        status=JobStatus.IDLE
    )
    cmd.status = JobStatus.IDLE
    await cmd.save()


async def recreate_command(conf: Config, command_id: int):
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    await delete_jobs_from_command(command_id)

    await create_jobs(conf, cmd)
    cmd.status = JobStatus.IDLE
    await cmd.save()


async def get_command(command_id: int) -> CommandOutput:
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    total_jobs = await JobRecord.filter(command_id=cmd.id).count()
    finished_jobs = await JobRecord.filter(
        command_id=cmd.id, status=JobStatus.FINISHED
    ).count()

    return CommandOutput(
        id=cmd.id,
        project_id=cmd.project_id,
        order=cmd.order,
        name=cmd.name,
        status=cmd.status,
        description=cmd.description,
        command_code=cmd.command_code,
        command_json=cmd.command_json,
        total_jobs=total_jobs,
        finished_jobs=finished_jobs,
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
        name=input.name,
        description=input.description,
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
        cmd.name = input.name
        cmd.description = input.description
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
        name=command.name,
        description=command.description,
        status=command.status,
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
        cout = await serialize_command(cmd)
        out.append(cout)
    return out


async def list_commands_paginated(
    project_id: int,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedOutput:
    offset = (page - 1) * page_size
    query = CommandRecord.filter(project_id=project_id).order_by("order")
    total = await query.count()
    items = await query.offset(offset).limit(page_size).all()
    cmds = [await serialize_command(item) for item in items]
    for cmd in cmds:
        total_jobs = await JobRecord.filter(command_id=cmd.id).count()
        finished_jobs = await JobRecord.filter(
            command_id=cmd.id, status=JobStatus.FINISHED
        ).count()
        cmd.total_jobs = total_jobs
        cmd.finished_jobs = finished_jobs

    return PaginatedOutput(
        items=cmds,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


async def download_file_for_command(conf: Config, command_id: int) -> str:
    cmd = await CommandRecord.get_or_none(id=command_id)
    if cmd is None:
        raise ValueError("command doesn't exist")

    if cmd.status != JobStatus.FINISHED:
        raise ValueError("command is not finished")

    jobs = await JobRecord.filter(command_id=cmd.id)

    job_filenames = [Path(job.result_img) for job in jobs]
    cmd.download_file = os.path.abspath(
        os.path.join(conf.downloads_path, str(cmd.id) + ".zip")
    )

    job_dicts = await JobRecord.filter(command_id=cmd.id).values(
        "prompt_positive", "prompt_negative", "lora_list"
    )
    print(job_dicts)
    json_str = json.dumps(job_dicts, indent=2, ensure_ascii=False)
    json_path = os.path.abspath(
        os.path.join(conf.downloads_path, str(cmd.id) + ".json")
    )
    async with aiofiles.open(json_path, mode="w", encoding="utf-8") as f:
        await f.write(json_str)
    job_filenames.append(Path(json_path))
    await create_zip(job_filenames, cmd.download_file)
    await cmd.save()
    return cmd.download_file

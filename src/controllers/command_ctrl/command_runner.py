import os
import uuid
from itertools import product

from src.controllers.command_ctrl.command_ctrl import CommandOutput
from src.controllers.command_ctrl.command_parser import PromptLanguageParser
from src.controllers.manager_ctrl import Manager
from src.core.config import Config
from src.db.records import (
    GroupRecord,
    ItemRecord,
    JobRecord,
    ServerRecord,
    WorkflowRecord,
)


async def run_command(conf: Config, manager: Manager, command: CommandOutput):
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
        group_code = group_sel.group_code_name

        # Check group exists
        group = await GroupRecord.filter(code_name=group_code).first()
        if not group:
            raise ValueError(f"Group '{group_code}' not found")

        items: list[ItemRecord] = []
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

    for items in combined_items:
        prompt_positive = ""
        prompt_negative = ""
        reference_controlnet_img = None
        reference_ipadapter_img = None
        lora_list = []
        result_img = os.path.join(conf.result_path, str(uuid.uuid4()) + ".png")

        group_item_id_list = []
        for item in items:
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
        await manager.add_job(job)

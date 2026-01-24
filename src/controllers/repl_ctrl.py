import json
import os
import re

from src.controllers.ctrl_types import JobOutput, ReplInput
from src.controllers.manager_ctrl import Manager
from src.controllers.serializers import serialize_job
from src.core.config import Config
from src.db.records import GeneratorRecord, GroupRecord, JobRecord, ServerRecord
from src.db.records.item_rec import ItemRecord


def serialize_group_item_code_names_to_dict(input_string):
    # Pattern to match group(item) format
    pattern = r"(\w+)\((\w+)\)"

    # Find all matches
    matches = re.findall(pattern, input_string)

    # Convert to list of dictionaries
    result = [
        {"group_code_name": group, "item_code_name": item} for group, item in matches
    ]

    return result


def validate_group_item_code_names(input: str):
    """
    Validates the input string format: group1(item1),group2(item2),...

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not input:
        return False, "Input string is empty"

    # Check for valid pattern: word(word) separated by commas
    # This pattern ensures the entire string matches the expected format
    full_pattern = r"^(\w+\(\w+\))(\,\w+\(\w+\))*$"

    if not re.match(full_pattern, input):
        return False, "Invalid format. Expected format: group1(item1),group2(item2),..."

    # Additional checks
    parts = input.split(",")
    for i, part in enumerate(parts, 1):
        # Check for empty group or item
        match = re.match(r"^(\w+)\((\w+)\)$", part)
        if not match:
            return False, f"Invalids format in part {i}: '{part}'"

        group, item = match.groups()

        if not group:
            return False, f"Empty group name in part {i}"
        if not item:
            return False, f"Empty item name in part {i}"

    return True, None


async def get_previous_job_from_repl() -> JobOutput | None:
    job_rec = await JobRecord.get_or_none(project_id=-1, command_id=-1)
    if job_rec is None:
        return None

    return serialize_job(job_rec)


async def run_repl(conf: Config, manager: Manager, input: ReplInput):
    server = await ServerRecord.filter(code_name=input.server_code_name).first()
    if server is None:
        raise ValueError(f"Server '{input.server_code_name}' not found")

    workflow = await GeneratorRecord.filter(code_name=input.generator_code_name).first()
    if workflow is None:
        raise ValueError(f"Workflow '{input.generator_code_name}' not found")

    if len(input.group_item_code_names) > 0:
        ok, err = validate_group_item_code_names(input.group_item_code_names)
        if not ok:
            raise ValueError(f"List of items is not valid: {err}")

    list_group_item_code_names = serialize_group_item_code_names_to_dict(
        input.group_item_code_names
    )
    prompt_positive = ""
    prompt_negative = ""
    reference_controlnet_img = None
    reference_ipadapter_img = None
    lora_list = []

    group_item_id_list = []
    for v in list_group_item_code_names:
        group = await GroupRecord.get_or_none(code_name=v["group_code_name"])
        if group is None:
            raise ValueError(f"Group '{v['group_code_name']}' not found")

        item = await ItemRecord.get_or_none(
            group_id=group.id, code_name=v["item_code_name"]
        )
        if item is None:
            raise ValueError(
                f"Item '{v['item_code_name']}' from group '{v['group_code_name']}' not found"
            )

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

        # if item.ipadapter_reference_image is not None:
        #     reference_ipadapter_img = item.ipadapter_reference_image

        if item.lora is not None:
            lora_list.append(item.lora)

    prompt_positive += input.prompt_positive
    prompt_negative += input.prompt_negative

    if len(input.lora_list) > 0:
        dict_lora_list = json.loads(input.lora_list)
        for v in dict_lora_list:
            if "name" not in v.keys():
                raise ValueError("LoRA doesn't have 'name' field")

            if "strength_model" not in v.keys():
                raise ValueError("LoRA doesn't have 'strength_model' field")

            if "strength_clip" not in v.keys():
                raise ValueError("LoRA doesn't have 'strength_clip' field")

        lora_list.extend(dict_lora_list)

    result_img = os.path.join(conf.result_path, "repl.png")

    await clear_repl_job()

    job = await JobRecord.create(
        project_id=-1,
        command_id=-1,
        group_item_id_list=group_item_id_list,
        code_str=input.group_item_code_names,
        server_code_name=server.code_name,
        server_host=server.host,
        generator_code_name=workflow.code_name,
        prompt_positive=prompt_positive,
        prompt_negative=prompt_negative,
        reference_controlnet_img=reference_controlnet_img,
        reference_ipadapter_img=reference_ipadapter_img,
        lora_list=lora_list,
        result_img=result_img,
    )

    await job.save()
    await manager.add_job(job.id)


async def clear_repl_job():
    job = await JobRecord.get_or_none(project_id=-1, command_id=-1)
    if job is not None:
        if job.result_img is not None:
            if os.path.exists(job.result_img):
                os.remove(job.result_img)
        await job.delete()

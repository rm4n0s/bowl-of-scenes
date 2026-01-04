import os
from dataclasses import dataclass
from typing import Any

from src.controllers.manager_ctrl import Manager
from src.db.records import ItemRecord, JobRecord
from src.db.records.job_rec import JobStatus


@dataclass
class JobOutput:
    id: int
    project_id: int
    command_id: int
    group_item_id_list: list[dict[str, Any]]
    code_str: str
    server_code_name: str
    server_host: str
    status: JobStatus
    workflow_code_name: str
    comfyui_prompt_id: str | None
    prompt_positive: str
    prompt_negative: str
    reference_controlnet_img: str | None
    reference_ipadapter_img: str | None
    lora_list: list[dict[str, Any]]
    result_img: str
    show_result_img: str


async def run_job(manager: Manager, job_id: int):
    job = await JobRecord.get_or_none(id=job_id)
    if job is None:
        raise ValueError("job doesn't exist")

    if job.status == JobStatus.WAITING:
        await manager.add_job(job)


async def reload_job(manager: Manager, job_id: int):
    job = await JobRecord.get_or_none(id=job_id)
    if job is None:
        raise ValueError("job doesn't exist")

    prompt_positive = ""
    prompt_negative = ""
    reference_controlnet_img = None
    reference_ipadapter_img = None
    lora_list = []

    for v in job.group_item_id_list:
        item = await ItemRecord.get_or_none(id=v["item_id"])
        if item is None:
            continue

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

    job.prompt_positive = prompt_positive
    job.prompt_negative = prompt_negative
    job.status = JobStatus.WAITING
    if reference_controlnet_img is not None:
        job.reference_controlnet_img = reference_controlnet_img
    if reference_ipadapter_img is not None:
        job.reference_ipadapter_img = reference_ipadapter_img
    job.lora_list = lora_list
    await job.save()

    await manager.add_job(job)


async def list_jobs(command_id: int) -> list[JobOutput]:
    jobs = await JobRecord.filter(command_id=command_id).all()
    ls = []
    for job in jobs:
        ls.append(
            JobOutput(
                id=job.id,
                project_id=job.project_id,
                command_id=job.command_id,
                group_item_id_list=job.group_item_id_list,
                code_str=job.code_str,
                server_code_name=job.server_code_name,
                server_host=job.server_host,
                status=job.status,
                workflow_code_name=job.workflow_code_name,
                comfyui_prompt_id=job.comfyui_prompt_id,
                prompt_positive=job.prompt_positive,
                prompt_negative=job.prompt_negative,
                reference_controlnet_img=job.reference_controlnet_img,
                reference_ipadapter_img=job.reference_ipadapter_img,
                lora_list=job.lora_list,
                result_img=job.result_img,
                show_result_img=f"/result_path/{os.path.basename(job.result_img)}",
            )
        )

    return ls

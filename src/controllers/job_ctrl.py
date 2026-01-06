from src.controllers.ctrl_types import JobOutput, serialize_job
from src.controllers.manager_ctrl import Manager
from src.db.records import ItemRecord, JobRecord
from src.db.records.job_rec import JobStatus


async def run_job(manager: Manager, job_id: int):
    job = await JobRecord.get_or_none(id=job_id)
    if job is None:
        raise ValueError("job doesn't exist")

    if job.status == JobStatus.WAITING:
        await manager.add_job(serialize_job(job))


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

    await manager.add_job(serialize_job(job))


async def list_jobs(command_id: int) -> list[JobOutput]:
    jobs = await JobRecord.filter(command_id=command_id).all()
    ls = []
    for job in jobs:
        ls.append(serialize_job(job))

    return ls

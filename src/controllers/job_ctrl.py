from src.controllers.ctrl_types import JobOutput
from src.controllers.manager_ctrl import Manager
from src.controllers.serializers import serialize_job
from src.db.records import ItemRecord, JobRecord
from src.db.records.item_rec import IPAdapter
from src.db.records.job_rec import JobStatus


async def run_job(manager: Manager, job_id: int):
    job = await JobRecord.get_or_none(id=job_id)
    if job is None:
        raise ValueError("job doesn't exist")

    if job.status == JobStatus.WAITING:
        await manager.add_job(job.id)


async def reload_job(manager: Manager, job_id: int):
    job = await JobRecord.get_or_none(id=job_id)
    if job is None:
        raise ValueError("job doesn't exist")

    prompt_positive = ""
    prompt_negative = ""
    reference_controlnet_img = None
    ipadapters: list[IPAdapter] = []
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

        if item.ipadapter is not None:
            ipadapters.append(item.ipadapter)

        if item.lora is not None:
            lora_list.append(item.lora)

    job.prompt_positive = prompt_positive
    job.prompt_negative = prompt_negative
    job.status = JobStatus.WAITING
    if reference_controlnet_img is not None:
        job.reference_controlnet_img = reference_controlnet_img

    job.ipadapter_list = ipadapters
    job.lora_list = lora_list
    await job.save()

    await manager.add_job(job.id)


async def list_jobs(command_id: int) -> list[JobOutput]:
    jobs = await JobRecord.filter(command_id=command_id).all()
    ls = []
    for job in jobs:
        ls.append(serialize_job(job))

    return ls

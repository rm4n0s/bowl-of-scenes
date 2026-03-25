from src.controllers.ctrl_types import IPAdapter, JobOutput, JobStatus
from src.controllers.manager_ctrl import Manager
from src.controllers.serializers import serialize_job
from src.core.utils.paginator import PaginatedOutput
from src.db.records import ItemRecord, JobRecord


async def run_job(manager: Manager, job_id: int):
    job = await JobRecord.get_or_none(id=job_id)
    if job is None:
        raise ValueError("job doesn't exist")

    if job.status == JobStatus.IDLE:
        job.status = JobStatus.QUEUED
        await job.save()
        await manager.add_job(job.id)


async def stop_job(manager: Manager, job_id: int):
    job = await JobRecord.get_or_none(id=job_id)
    if job is None:
        raise ValueError("job doesn't exist")

    if job.status == JobStatus.QUEUED:
        job.status = JobStatus.IDLE
        await job.save()


async def reload_job(manager: Manager, job_id: int):
    job = await JobRecord.get_or_none(id=job_id)
    if job is None:
        raise ValueError("job doesn't exist")

    prompt_positive = ""
    prompt_negative = ""
    ipadapters: list[IPAdapter] = []
    lora_list = []

    for v in job.group_item_id_list:
        item = await ItemRecord.get_or_none(id=v["item_id"])
        if item is None:
            continue

        if len(item.positive_prompt) > 0:
            prompt_positive += item.positive_prompt + " "
        if len(item.negative_prompt) > 0:
            prompt_negative += item.negative_prompt + " "

        if item.ipadapter is not None:
            ipadapters.append(item.ipadapter)

        if item.lora_list is not None:
            lora_list.append(item.lora_list)

    job.prompt_positive = prompt_positive
    job.prompt_negative = prompt_negative
    job.status = JobStatus.IDLE
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


async def list_jobs_paginated(
    command_id: int,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedOutput:
    offset = (page - 1) * page_size

    total = await JobRecord.filter(command_id=command_id).count()
    jobs = (
        await JobRecord.filter(command_id=command_id)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return PaginatedOutput(
        items=[serialize_job(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )

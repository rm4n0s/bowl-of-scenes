import os

from src.controllers.ctrl_types import ProjectInput, ProjectOutput
from src.db.records import JobRecord, ProjectRecord
from src.db.records.command_rec import CommandRecord


async def add_project(input: ProjectInput):
    await ProjectRecord.create(
        name=input.name,
    )


async def edit_project(id: int, input: ProjectInput):
    project = await ProjectRecord.get_or_none(id=id)
    if project is None:
        raise ValueError("Project does not exist")

    project.name = input.name
    await project.save()


async def delete_project(id: int):
    project = await ProjectRecord.get_or_none(id=id)
    if project is None:
        raise ValueError("Project does not exist")

    jobs = await JobRecord.filter(project_id=id).all()
    for job in jobs:
        if job.result_img is not None:
            if os.path.exists(job.result_img):
                os.remove(job.result_img)

        await job.delete()

    cmds = await CommandRecord.filter(project_id=id).all()
    for cmd in cmds:
        await cmd.delete()

    await project.delete()


async def list_projects() -> list[ProjectOutput]:
    cat_recs = await ProjectRecord.all()
    cat_outs = []
    for ct in cat_recs:
        co = ProjectOutput(
            id=ct.id,
            name=ct.name,
        )
        cat_outs.append(co)

    return cat_outs


async def get_project(id: int) -> ProjectOutput | None:
    rec = await ProjectRecord.get_or_none(id=id)
    if rec is None:
        return None

    return ProjectOutput(
        id=rec.id,
        name=rec.name,
    )

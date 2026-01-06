from src.controllers.ctrl_types import ProjectInput, ProjectOutput
from src.db.records import ProjectRecord


async def add_project(input: ProjectInput):
    await ProjectRecord.create(
        name=input.name,
    )


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

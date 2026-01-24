from src.controllers.ctrl_types import FixerInput, FixerOutput
from src.controllers.serializers import serialize_fixer
from src.db.records import FixerRecord


async def list_fixers() -> list[FixerOutput]:
    recs = await FixerRecord.all()
    outs = []
    for rec in recs:
        f = serialize_fixer(rec)
        outs.append(f)

    return outs


async def add_fixer(input: FixerInput):
    await FixerRecord.create(
        name=input.name,
        code_name=input.code_name,
        positive_prompt=input.positive_prompt,
        negative_prompt=input.negative_prompt,
        load_image_title=input.load_image_title,
        save_image_title=input.save_image_title,
        workflow_json=input.workflow_json,
    )


async def edit_fixer(id: int, input: FixerInput):
    fixer = await FixerRecord.get_or_none(id=id)
    if fixer is None:
        raise ValueError("fixer doesn't exist")

    fixer.name = input.name
    fixer.code_name = input.code_name
    fixer.positive_prompt = input.positive_prompt
    fixer.negative_prompt = input.negative_prompt
    fixer.load_image_title = input.load_image_title
    fixer.save_image_title = input.save_image_title
    fixer.workflow_json = input.workflow_json
    await fixer.save()


async def delete_fixer(id: int):
    fixer = await FixerRecord.get_or_none(id=id)
    if fixer is None:
        raise ValueError("fixer doesn't exist")

    await fixer.delete()

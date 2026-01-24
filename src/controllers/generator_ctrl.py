from src.controllers.ctrl_types import GeneratorInput, GeneratorOutput
from src.db.records import GeneratorRecord


async def add_generator(input: GeneratorInput):
    await GeneratorRecord.create(
        name=input.name,
        code_name=input.code_name,
        positive_prompt_title=input.positive_prompt_title,
        negative_prompt_title=input.negative_prompt_title,
        load_image_controlnet_title=input.load_image_controlnet_title,
        save_image_title=input.save_image_title,
        workflow_json=input.workflow_json,
    )


async def edit_generator(id: int, input: GeneratorInput):
    gen = await GeneratorRecord.get_or_none(id=id)
    if gen is None:
        raise ValueError("workflow doesn't exist")

    gen.name = input.name
    gen.code_name = input.code_name
    if input.positive_prompt_title is not None:
        gen.positive_prompt_title = input.positive_prompt_title

    if input.negative_prompt_title is not None:
        gen.negative_prompt_title = input.negative_prompt_title

    if input.load_image_controlnet_title is not None:
        gen.load_image_controlnet_title = input.load_image_controlnet_title

    gen.save_image_title = input.save_image_title
    gen.workflow_json = input.workflow_json

    await gen.save()


async def list_generators() -> list[GeneratorOutput]:
    gen_recs = await GeneratorRecord.all()
    gen_outs = []
    for gen in gen_recs:
        gout = GeneratorOutput(
            id=gen.id,
            name=gen.name,
            code_name=gen.code_name,
            workflow_json=gen.workflow_json,
            positive_prompt_title=gen.positive_prompt_title,
            negative_prompt_title=gen.negative_prompt_title,
            load_image_controlnet_title=gen.load_image_controlnet_title,
            save_image_title=gen.save_image_title,
        )
        gen_outs.append(gout)
    return gen_outs


async def delete_generator(id: int):
    gen = await GeneratorRecord.get_or_none(id=id)
    if gen is None:
        raise ValueError("workflow doesn't exist")

    await gen.delete()

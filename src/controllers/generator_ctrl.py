from dataclasses import asdict

from src.controllers.ctrl_types import (
    GeneratorInput,
    GeneratorOutput,
    GeneratorOutputType,
    ImageAttributes,
    ThreeDAttributes,
    VideoAttributes,
)
from src.db.records import GeneratorRecord


async def add_generator(input: GeneratorInput):
    output_attr = None
    if input.output_attributes is not None:
        output_attr = asdict(input.output_attributes)

    await GeneratorRecord.create(
        name=input.name,
        code_name=input.code_name,
        positive_prompt_title=input.positive_prompt_title,
        negative_prompt_title=input.negative_prompt_title,
        workflow_json=input.workflow_json,
        has_random_seed=input.has_random_seed,
        output_type=input.output_type,
        output_attributes=output_attr,
        output_node_class_type=input.output_node_class_type,
        output_node_title=input.output_node_title,
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

    gen.has_random_seed = input.has_random_seed
    gen.workflow_json = input.workflow_json

    gen.output_type = input.output_type
    if input.output_attributes is not None:
        gen.output_attributes = asdict(input.output_attributes)

    gen.output_node_class_type = input.output_node_class_type
    gen.output_node_title = input.output_node_title
    await gen.save()


async def list_generators() -> list[GeneratorOutput]:
    gen_recs = await GeneratorRecord.all()
    gen_outs = []
    for gen in gen_recs:
        attrs = None
        match gen.output_type:
            case GeneratorOutputType.IMAGE:
                attrs = ImageAttributes(**gen.output_attributes)
            case GeneratorOutputType.VIDEO:
                attrs = VideoAttributes(**gen.output_attributes)
            case GeneratorOutputType.THREE_D:
                attrs = ThreeDAttributes(**gen.output_attributes)

        gout = GeneratorOutput(
            id=gen.id,
            name=gen.name,
            code_name=gen.code_name,
            workflow_json=gen.workflow_json,
            positive_prompt_title=gen.positive_prompt_title,
            negative_prompt_title=gen.negative_prompt_title,
            output_type=gen.output_type,
            output_attributes=attrs,
            output_node_class_type=gen.output_node_class_type,
            output_node_title=gen.output_node_title,
            has_random_seed=gen.has_random_seed,
        )
        gen_outs.append(gout)
    return gen_outs


async def delete_generator(id: int):
    gen = await GeneratorRecord.get_or_none(id=id)
    if gen is None:
        raise ValueError("workflow doesn't exist")

    await gen.delete()

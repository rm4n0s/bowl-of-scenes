from dataclasses import asdict

from src.controllers.ctrl_types import (
    GeneratorInput,
    GeneratorOutput,
    GeneratorOutputType,
    ImageAttributes,
    ThreeDAttributes,
    VideoAttributes,
)
from src.controllers.serializers import serialize_generator
from src.core.utils.paginator import PaginatedOutput
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
        gout = serialize_generator(gen)
        gen_outs.append(gout)
    return gen_outs


async def list_generators_paginated(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedOutput:
    offset = (page - 1) * page_size

    total = await GeneratorRecord.all().count()
    items = await GeneratorRecord.all().offset(offset).limit(page_size)

    return PaginatedOutput(
        items=[serialize_generator(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


async def delete_generator(id: int):
    gen = await GeneratorRecord.get_or_none(id=id)
    if gen is None:
        raise ValueError("workflow doesn't exist")

    await gen.delete()

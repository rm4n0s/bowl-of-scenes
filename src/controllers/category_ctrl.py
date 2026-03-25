from src.controllers.ctrl_types import CategoryInput, CategoryOutput
from src.controllers.serializers import serialize_category
from src.core.utils.paginator import PaginatedOutput
from src.db.records import CategoryRecord


async def add_category(input: CategoryInput):
    await CategoryRecord.create(
        name=input.name,
    )


async def edit_category(id: int, input: CategoryInput):
    cat = await CategoryRecord.get_or_none(id=id)
    if cat is None:
        raise ValueError("category doesn't exist")

    if cat.name != input.name:
        cat.name = input.name
        await cat.save()


async def list_categories() -> list[CategoryOutput]:
    cat_recs = await CategoryRecord.all()
    cat_outs = []
    for ct in cat_recs:
        co = serialize_category(ct)
        cat_outs.append(co)

    return cat_outs


async def list_categories_paginated(
    page: int = 1,
    page_size: int = 20,
) -> PaginatedOutput:
    offset = (page - 1) * page_size

    total = await CategoryRecord.all().count()
    items = await CategoryRecord.all().offset(offset).limit(page_size)

    return PaginatedOutput(
        items=[serialize_category(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


async def init_predefined_categories():
    categories = [
        "none",
        "character",
        "poses",
        "style",
        "clothe",
        "body",
        "emotion",
        "quality",
        "background",
        "camera",
    ]
    for name in categories:
        exists = await CategoryRecord.exists(name=name)
        if not exists:
            await add_category(CategoryInput(name=name))

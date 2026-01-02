from dataclasses import dataclass

from src.db.records import CategoryRecord


@dataclass
class CategoryInput:
    name: str


@dataclass
class CategoryOutput:
    id: int
    name: str


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
        co = CategoryOutput(
            id=ct.id,
            name=ct.name,
        )
        cat_outs.append(co)

    return cat_outs


async def init_predefined_categories():
    categories = [
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

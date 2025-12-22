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
    categories = ["character", "pose", "style", "clothes", "body", "emotions"]
    for name in categories:
        exists = await CategoryRecord.exists(name=name)
        if not exists:
            await add_category(CategoryInput(name=name))

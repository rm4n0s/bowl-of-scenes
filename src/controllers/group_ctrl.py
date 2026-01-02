import os
import uuid
from dataclasses import dataclass

from nicegui.elements.upload_files import FileUpload

from src.core.config import Config
from src.db.records import GroupRecord


@dataclass
class GroupInput:
    name: str
    description: str
    code_name: str
    category_id: int
    use_lora: bool
    use_controlnet: bool
    use_ip_adapter: bool
    thumbnail_image: FileUpload | None


@dataclass
class GroupOutput:
    id: int
    name: str
    description: str
    code_name: str
    category_id: int
    use_lora: bool
    use_controlnet: bool
    use_ip_adapter: bool
    thumbnail_image: str | None


async def add_group(conf: Config, input: GroupInput):
    thumbnail_path = None
    if input.thumbnail_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.thumbnail_image.name
        thumbnail_path = os.path.join(conf.thumbnails_path, image_filename)
        await input.thumbnail_image.save(thumbnail_path)

    await GroupRecord.create(
        name=input.name,
        description=input.description,
        code_name=input.code_name,
        category_id=input.category_id,
        use_lora=input.use_lora,
        use_controlnet=input.use_controlnet,
        use_ip_adapter=input.use_ip_adapter,
        thumbnail_image=thumbnail_path,
    )


async def edit_group(conf: Config, id: int, input: GroupInput):
    group = await GroupRecord.get_or_none(id=id)
    if group is None:
        raise ValueError("group doesn't exist")

    if group.name != input.name:
        group.name = input.name

    if group.code_name != input.code_name:
        group.code_name = input.code_name

    if group.description != input.description:
        group.description = input.description

    if group.category_id != input.category_id:
        group.category_id = input.category_id

    if group.use_lora != input.use_lora:
        group.use_lora = input.use_lora

    if group.use_ip_adapter != input.use_ip_adapter:
        group.use_ip_adapter = input.use_ip_adapter

    if group.use_controlnet != input.use_controlnet:
        group.use_controlnet = input.use_controlnet

    if input.thumbnail_image is not None:
        if group.thumbnail_image is not None:
            image_filename = group.thumbnail_image
        else:
            image_filename = str(uuid.uuid4()) + "_" + input.thumbnail_image.name

        thumbnail_path = os.path.join(conf.thumbnails_path, image_filename)
        await input.thumbnail_image.save(thumbnail_path)
        group.thumbnail_image = thumbnail_path

    await group.save()


async def list_groups() -> list[GroupOutput]:
    recs = await GroupRecord.all()
    outs = []
    for rec in recs:
        go = GroupOutput(
            id=rec.id,
            name=rec.name,
            description=rec.description,
            code_name=rec.code_name,
            category_id=rec.category_id,
            use_lora=rec.use_lora,
            use_controlnet=rec.use_controlnet,
            use_ip_adapter=rec.use_ip_adapter,
            thumbnail_image=rec.thumbnail_image,
        )
        outs.append(go)

    return outs


async def get_group(id: int) -> GroupOutput | None:
    rec = await GroupRecord.get_or_none(id=id)
    if rec is None:
        return None

    return GroupOutput(
        id=rec.id,
        name=rec.name,
        description=rec.description,
        code_name=rec.code_name,
        category_id=rec.category_id,
        use_lora=rec.use_lora,
        use_controlnet=rec.use_controlnet,
        use_ip_adapter=rec.use_ip_adapter,
        thumbnail_image=rec.thumbnail_image,
    )

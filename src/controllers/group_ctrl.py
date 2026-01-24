import os
import uuid

from src.controllers.common import delete_item_files
from src.controllers.ctrl_types import GroupInput, GroupOutput
from src.controllers.serializers import serialize_group
from src.core.config import Config
from src.db.records import GroupRecord, ItemRecord


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
        use_mask_region=input.use_mask_region,
        use_coordinates_region=input.use_coordinates_region,
        thumbnail_image=thumbnail_path,
    )


async def add_group_of_positives_from_text_file(
    name: str, description: str, code_name: str, category_id: int, text_content: str
):
    group = await GroupRecord.create(
        name=name,
        description=description,
        code_name=code_name,
        category_id=category_id,
        use_lora=False,
        use_controlnet=False,
        use_ip_adapter=False,
        use_mask_region=False,
        use_coordinates_region=False,
        thumbnail_image=None,
    )

    for i, v in enumerate(text_content.splitlines()):
        await ItemRecord.create(
            group_id=group.id,
            name=f"{i}",
            code_name=f"{i}",
            positive_prompt=v,
            negative_prompt="",
            lora=None,
            controlnet_reference_image=None,
            ipadapter_reference_image=None,
            mask_region_images=None,
            thumbnail_image=None,
        )


async def edit_group(conf: Config, id: int, input: GroupInput):
    group = await GroupRecord.get_or_none(id=id)
    if group is None:
        raise ValueError("group doesn't exist")

    group.name = input.name
    group.code_name = input.code_name
    group.description = input.description
    group.category_id = input.category_id
    group.use_lora = input.use_lora
    group.use_ip_adapter = input.use_ip_adapter
    group.use_controlnet = input.use_controlnet
    group.use_mask_region = input.use_mask_region
    group.use_coordinates_region = input.use_coordinates_region

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
        go = serialize_group(rec)
        outs.append(go)

    return outs


async def get_group(id: int) -> GroupOutput | None:
    rec = await GroupRecord.get_or_none(id=id)
    if rec is None:
        return None

    return serialize_group(rec)


async def delete_group(id: int):
    rec = await GroupRecord.get_or_none(id=id)
    if rec is None:
        raise ValueError("Group doesn't exist")

    items = await ItemRecord.filter(group_id=id).all()
    for item in items:
        await delete_item_files(item)

        await item.delete()

    await rec.delete()

import os
import uuid
from dataclasses import dataclass

from nicegui.elements.upload_files import FileUpload

from src.core.config import Config
from src.db.records import ItemRecord


@dataclass
class ItemInput:
    group_id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    controlnet_reference_image: FileUpload | None
    ipadapter_reference_image: FileUpload | None
    thumbnail_image: FileUpload | None


@dataclass
class ItemOutput:
    id: int
    group_id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    controlnet_reference_image: str | None
    ipadapter_reference_image: str | None
    thumbnail_image: str | None


async def add_item(conf: Config, input: ItemInput):
    thumbnail_path = None
    if input.thumbnail_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.thumbnail_image.name
        thumbnail_path = os.path.join(conf.thumbnails_path, image_filename)
        await input.thumbnail_image.save(thumbnail_path)

    ipadapter_ref_path = None
    if input.ipadapter_reference_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.ipadapter_reference_image.name
        ipadapter_ref_path = os.path.join(
            conf.ipadapter_references_path, image_filename
        )
        await input.ipadapter_reference_image.save(ipadapter_ref_path)

    controlnt_ref_path = None
    if input.controlnet_reference_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.controlnet_reference_image.name
        controlnt_ref_path = os.path.join(
            conf.controlnet_references_path, image_filename
        )
        await input.controlnet_reference_image.save(controlnt_ref_path)

    await ItemRecord.create(
        group_id=input.group_id,
        name=input.name,
        code_name=input.code_name,
        positive_prompt=input.positive_prompt,
        negative_prompt=input.negative_prompt,
        controlnet_reference_image=controlnt_ref_path,
        ipadapter_reference_image=ipadapter_ref_path,
        thumbnail_image=thumbnail_path,
    )


async def list_items(group_id: int) -> list[ItemOutput]:
    recs = await ItemRecord.filter(group_id=group_id)
    outs = []
    for rec in recs:
        io = ItemOutput(
            id=rec.id,
            group_id=rec.group_id,
            name=rec.name,
            code_name=rec.code_name,
            positive_prompt=rec.positive_prompt,
            negative_prompt=rec.negative_prompt,
            controlnet_reference_image=rec.controlnet_reference_image,
            ipadapter_reference_image=rec.ipadapter_reference_image,
            thumbnail_image=rec.thumbnail_image,
        )
        outs.append(io)
    return outs

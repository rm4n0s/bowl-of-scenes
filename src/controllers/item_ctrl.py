import json
import os
import shutil
import uuid
from dataclasses import asdict

from src.controllers.common import delete_item_files
from src.controllers.ctrl_types import ItemInput, ItemOutput
from src.controllers.serializers import serialize_item
from src.core.config import Config
from src.core.utils.auto_masking import auto_create_masks
from src.db.records import ItemRecord
from src.db.records.item_rec import IPAdapter, MaskRegionImages


async def add_item(conf: Config, input: ItemInput):
    code_name_exists = await ItemRecord.filter(
        group_id=input.group_id, code_name=input.code_name
    ).exists()
    if code_name_exists:
        raise ValueError("code name already exists in group")

    thumbnail_path = None
    if input.thumbnail_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.thumbnail_image.name
        thumbnail_path = os.path.join(conf.thumbnails_path, image_filename)
        await input.thumbnail_image.save(thumbnail_path)

    ipadapter = None
    if input.ipadapter is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.ipadapter.reference_image.name
        ipadapter_ref_path = os.path.join(
            conf.ipadapter_references_path, image_filename
        )
        await input.ipadapter.reference_image.save(ipadapter_ref_path)
        ipadapter = asdict(
            IPAdapter(
                image_file=ipadapter_ref_path,
                weight=input.ipadapter.weight,
                weight_type=input.ipadapter.weight_type,
                start_at=input.ipadapter.start_at,
                end_at=input.ipadapter.end_at,
                clip_vision_model=input.ipadapter.clip_vision_model,
                model_name=input.ipadapter.model_name,
            )
        )

    controlnt_ref_path = None
    if input.controlnet_reference_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.controlnet_reference_image.name
        controlnt_ref_path = os.path.join(
            conf.controlnet_references_path, image_filename
        )
        await input.controlnet_reference_image.save(controlnt_ref_path)

    mask_region_images = None
    if input.mask_region_reference_image is not None:
        photos_id = str(uuid.uuid4())
        image_filename = str(photos_id) + "_" + input.mask_region_reference_image.name
        cc_ref_path = os.path.join(conf.colored_region_path, image_filename)
        await input.mask_region_reference_image.save(cc_ref_path)
        mask_folder_path = os.path.join(conf.colored_region_path, photos_id)
        output = auto_create_masks(cc_ref_path, mask_folder_path)
        mask_files = {}
        for key, outpath in output.items():
            mask_files[key] = outpath

        mask_region_images = asdict(
            MaskRegionImages(
                reference_path=cc_ref_path,
                folder_path=mask_folder_path,
                mask_files=mask_files,
            )
        )

    coordinated_regions = None
    if input.coordinated_regions is not None and len(input.coordinated_regions) > 0:
        coordinated_regions = json.loads(input.coordinated_regions)

    lora = None
    if input.lora is not None and len(input.lora) > 0:
        lora = json.loads(input.lora)

    await ItemRecord.create(
        group_id=input.group_id,
        name=input.name,
        code_name=input.code_name,
        positive_prompt=input.positive_prompt,
        negative_prompt=input.negative_prompt,
        lora=lora,
        controlnet_reference_image=controlnt_ref_path,
        ipadapter=ipadapter,
        mask_region_images=mask_region_images,
        coordinated_regions=coordinated_regions,
        thumbnail_image=thumbnail_path,
    )


async def delete_item(id: int):
    item = await ItemRecord.get_or_none(id=id)
    if item is None:
        raise ValueError("Item doesn't exist")

    await delete_item_files(item)

    await item.delete()


async def edit_item(conf: Config, id: int, ui_input: ItemInput):
    item = await ItemRecord.get_or_none(id=id)
    if item is None:
        raise ValueError("item doesn't exist")

    item.name = ui_input.name
    item.code_name = ui_input.code_name
    item.positive_prompt = ui_input.positive_prompt
    item.negative_prompt = ui_input.negative_prompt

    if ui_input.lora is not None and len(ui_input.lora) > 0:
        item.lora = json.loads(ui_input.lora)

    if ui_input.thumbnail_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + ui_input.thumbnail_image.name
        thumbnail_path = os.path.join(conf.thumbnails_path, image_filename)
        await ui_input.thumbnail_image.save(thumbnail_path)
        item.thumbnail_image = thumbnail_path

    if ui_input.ipadapter is not None:
        image_filename = (
            str(uuid.uuid4()) + "_" + ui_input.ipadapter.reference_image.name
        )

        ipadapter_ref_path = os.path.join(
            conf.ipadapter_references_path, image_filename
        )
        await ui_input.ipadapter.reference_image.save(ipadapter_ref_path)
        item.ipadapter = asdict(
            IPAdapter(
                image_file=ipadapter_ref_path,
                weight=ui_input.ipadapter.weight,
                weight_type=ui_input.ipadapter.weight_type,
                start_at=ui_input.ipadapter.start_at,
                end_at=ui_input.ipadapter.end_at,
                clip_vision_model=ui_input.ipadapter.clip_vision_model,
                model_name=ui_input.ipadapter.model_name,
            )
        )

    if ui_input.controlnet_reference_image is not None:
        image_filename = (
            str(uuid.uuid4()) + "_" + ui_input.controlnet_reference_image.name
        )

        image_filename = (
            str(uuid.uuid4()) + "_" + ui_input.controlnet_reference_image.name
        )
        controlnt_ref_path = os.path.join(
            conf.controlnet_references_path, image_filename
        )
        await ui_input.controlnet_reference_image.save(controlnt_ref_path)
        item.controlnet_reference_image = controlnt_ref_path

    if ui_input.mask_region_reference_image is not None:
        photos_id = str(uuid.uuid4())
        image_filename = (
            str(photos_id) + "_" + ui_input.mask_region_reference_image.name
        )
        cc_ref_path = os.path.join(conf.colored_region_path, image_filename)
        await ui_input.mask_region_reference_image.save(cc_ref_path)
        mask_folder_path = os.path.join(conf.colored_region_path, photos_id)
        output = auto_create_masks(cc_ref_path, mask_folder_path)
        mask_files = {}
        for key, outpath in output.items():
            mask_files[key] = outpath

        mask_region_images = asdict(
            MaskRegionImages(
                reference_path=cc_ref_path,
                folder_path=mask_folder_path,
                mask_files=mask_files,
            )
        )
        item.mask_region_images = mask_region_images

    if (
        ui_input.coordinated_regions is not None
        and len(ui_input.coordinated_regions) > 0
    ):
        item.coordinated_regions = json.loads(ui_input.coordinated_regions)

    await item.save()


async def list_items(group_id: int) -> list[ItemOutput]:
    recs = await ItemRecord.filter(group_id=group_id)
    outs = []
    for rec in recs:
        io = serialize_item(rec)
        outs.append(io)
    return outs

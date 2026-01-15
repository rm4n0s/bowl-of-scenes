import json
import os
import uuid
from dataclasses import asdict
from turtle import color

from src.controllers.ctrl_types import ItemInput, ItemOutput
from src.core.config import Config
from src.core.utils.auto_masking import auto_create_masks
from src.db.records import ItemRecord
from src.db.records.item_rec import ColorCodeImages


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

    color_coded_images = None
    if input.color_coded_reference_image is not None:
        photos_id = str(uuid.uuid4())
        image_filename = str(photos_id) + "_" + input.color_coded_reference_image.name
        cc_ref_path = os.path.join(conf.colored_region_path, image_filename)
        await input.color_coded_reference_image.save(cc_ref_path)
        mask_folder_path = os.path.join(conf.colored_region_path, photos_id)
        output = auto_create_masks(cc_ref_path, mask_folder_path)
        mask_files = {}
        for key, outpath in output.items():
            mask_files[key] = outpath

        color_coded_images = asdict(
            ColorCodeImages(reference_path=cc_ref_path, mask_files=mask_files)
        )

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
        ipadapter_reference_image=ipadapter_ref_path,
        color_coded_images=color_coded_images,
        thumbnail_image=thumbnail_path,
    )


async def delete_item(id: int):
    item = await ItemRecord.get_or_none(id=id)
    if item is None:
        raise ValueError("Item doesn't exist")

    if item.ipadapter_reference_image is not None:
        if os.path.exists(item.ipadapter_reference_image):
            os.remove(item.ipadapter_reference_image)

    if item.controlnet_reference_image is not None:
        if os.path.exists(item.controlnet_reference_image):
            os.remove(item.controlnet_reference_image)

    if item.color_coded_images is not None:
        color_coded_images = ColorCodeImages(**item.color_coded_images)
        if os.path.exists(color_coded_images.reference_path):
            os.remove(color_coded_images.reference_path)

        for mf in color_coded_images.mask_files.values():
            if os.path.exists(mf):
                os.remove(mf)

        # TODO delete also the folder

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
        if item.thumbnail_image is not None:
            image_filename = item.thumbnail_image
        else:
            image_filename = str(uuid.uuid4()) + "_" + ui_input.thumbnail_image.name

        thumbnail_path = os.path.join(conf.thumbnails_path, image_filename)
        await ui_input.thumbnail_image.save(thumbnail_path)
        item.thumbnail_image = thumbnail_path

    if ui_input.ipadapter_reference_image is not None:
        if item.ipadapter_reference_image is not None:
            image_filename = item.ipadapter_reference_image
        else:
            image_filename = (
                str(uuid.uuid4()) + "_" + ui_input.ipadapter_reference_image.name
            )

        image_filename = (
            str(uuid.uuid4()) + "_" + ui_input.ipadapter_reference_image.name
        )
        ipadapter_ref_path = os.path.join(
            conf.ipadapter_references_path, image_filename
        )
        await ui_input.ipadapter_reference_image.save(ipadapter_ref_path)
        item.ipadapter_reference_image = ipadapter_ref_path

    if ui_input.controlnet_reference_image is not None:
        if item.controlnet_reference_image is not None:
            image_filename = item.controlnet_reference_image
        else:
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

    if ui_input.color_coded_reference_image is not None:
        photos_id = str(uuid.uuid4())
        image_filename = (
            str(photos_id) + "_" + ui_input.color_coded_reference_image.name
        )
        cc_ref_path = os.path.join(conf.colored_region_path, image_filename)
        await ui_input.color_coded_reference_image.save(cc_ref_path)
        mask_folder_path = os.path.join(conf.colored_region_path, photos_id)
        output = auto_create_masks(cc_ref_path, mask_folder_path)
        mask_files = {}
        for key, outpath in output.items():
            mask_files[key] = outpath

        color_coded_images = asdict(
            ColorCodeImages(reference_path=cc_ref_path, mask_files=mask_files)
        )
        item.color_coded_images = color_coded_images

    await item.save()


async def list_items(group_id: int) -> list[ItemOutput]:
    recs = await ItemRecord.filter(group_id=group_id)
    outs = []
    for rec in recs:
        lora = None
        if rec.lora is not None:
            lora = json.dumps(rec.lora)
        show_controlnet_reference_image = None
        if rec.controlnet_reference_image is not None:
            show_controlnet_reference_image = f"/controlnet_references_path/{os.path.basename(rec.controlnet_reference_image)}"
        show_ipadapter_reference_image = None
        if rec.ipadapter_reference_image is not None:
            show_ipadapter_reference_image = f"/ipadapter_references_path/{os.path.basename(rec.ipadapter_reference_image)}"
        show_thumbnail_image = None
        if rec.thumbnail_image is not None:
            show_thumbnail_image = (
                f"/thumbnails_path/{os.path.basename(rec.thumbnail_image)}"
            )

        color_coded_images = None
        color_coded_images_keys = None
        if rec.color_coded_images is not None:
            color_coded_images = ColorCodeImages(**rec.color_coded_images)
            color_coded_images_keys = f"{list(color_coded_images.mask_files.keys())}"

        io = ItemOutput(
            id=rec.id,
            group_id=rec.group_id,
            name=rec.name,
            code_name=rec.code_name,
            positive_prompt=rec.positive_prompt,
            negative_prompt=rec.negative_prompt,
            lora=lora,
            controlnet_reference_image=rec.controlnet_reference_image,
            show_controlnet_reference_image=show_controlnet_reference_image,
            ipadapter_reference_image=rec.ipadapter_reference_image,
            show_ipadapter_reference_image=show_ipadapter_reference_image,
            color_coded_images=color_coded_images,
            color_coded_images_keys=color_coded_images_keys,
            thumbnail_image=rec.thumbnail_image,
            show_thumbnail_image=show_thumbnail_image,
        )
        outs.append(io)
    return outs

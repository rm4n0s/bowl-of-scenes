import json
import os
import uuid
from dataclasses import asdict

from src.controllers.common import delete_item_files
from src.controllers.ctrl_types import (
    CivitaiLora,
    ControlNetConfig,
    IPAdapter,
    ItemInput,
    ItemOutput,
    Lora,
    MaskRegionImages,
)
from src.controllers.serializers import serialize_item
from src.core.config import Config
from src.core.utils import lora_downloader
from src.core.utils.auto_masking import auto_create_masks
from src.core.utils.paginator import PaginatedOutput
from src.db.records import ItemRecord


async def add_item(conf: Config, input: ItemInput):
    code_name_exists = await ItemRecord.filter(
        group_id=input.group_id, code_name=input.code_name
    ).exists()
    if code_name_exists:
        raise ValueError("code name already exists in group")

    thumbnail_path = None
    if input.thumbnail_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.thumbnail_image.name
        thumbnail_path = os.path.abspath(
            os.path.join(conf.thumbnails_path, image_filename)
        )
        await input.thumbnail_image.save(thumbnail_path)

    ipadapter = None
    if input.ipadapter is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.ipadapter.reference_image.name
        ipadapter_ref_path = os.path.abspath(
            os.path.join(conf.ipadapter_references_path, image_filename)
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

    output_type = None
    output_type_attributes = None
    if (
        input.generator_output_type is not None
        and input.generator_output_attributes is not None
    ):
        output_type = input.generator_output_type
        output_type_attributes = json.loads(input.generator_output_attributes)

    controlnets: list[ControlNetConfig] = []
    for input_cnc in input.controlnets:
        if input_cnc.image_path is None:
            continue

        photos_id = str(uuid.uuid4())
        image_filename = str(photos_id) + "_" + input_cnc.image_path.name
        cc_ref_path = os.path.abspath(
            os.path.join(conf.controlnet_references_path, image_filename)
        )
        await input_cnc.image_path.save(cc_ref_path)

        controlnets.append(
            ControlNetConfig(
                type_of_controlnet=input_cnc.type_of_controlnet,
                image_path=cc_ref_path,
                is_reference=input_cnc.is_reference,
                model_pattern=input_cnc.model_pattern,
                strength=input_cnc.strength,
            )
        )

    await ItemRecord.create(
        group_id=input.group_id,
        name=input.name,
        code_name=input.code_name,
        positive_prompt=input.positive_prompt,
        negative_prompt=input.negative_prompt,
        lora_list=lora,
        ipadapter=ipadapter,
        controlnets=controlnets,
        mask_region_images=mask_region_images,
        coordinated_regions=coordinated_regions,
        output_type=output_type,
        output_type_attributes=output_type_attributes,
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
        item.lora_list = json.loads(ui_input.lora)

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

    if len(ui_input.controlnets) > 0:
        controlnets: list[ControlNetConfig] = []
        for v in item.controlnets:
            controlnets.append(
                ControlNetConfig(
                    type_of_controlnet=v["type_of_controlnet"],
                    image_path=v["image_path"],
                    is_reference=v["is_reference"],
                    model_pattern=v["model_pattern"],
                    strength=v["strength"],
                )
            )
        existing_controlnets = {}
        for input_cnc in ui_input.controlnets:
            existing_controlnets[
                input_cnc.model_pattern
                + "_"
                + str(input_cnc.type_of_controlnet)
                + "_"
                + str(input_cnc.strength)
            ] = True
            if input_cnc.image_path is None:
                continue

            photos_id = str(uuid.uuid4())
            image_filename = str(photos_id) + "_" + input_cnc.image_path.name
            cc_ref_path = os.path.abspath(
                os.path.join(conf.controlnet_references_path, image_filename)
            )
            await input_cnc.image_path.save(cc_ref_path)

            controlnets.append(
                ControlNetConfig(
                    type_of_controlnet=input_cnc.type_of_controlnet,
                    image_path=cc_ref_path,
                    is_reference=input_cnc.is_reference,
                    model_pattern=input_cnc.model_pattern,
                    strength=input_cnc.strength,
                )
            )

        # to remove from the list whatever controlnet user deleted
        cons = []
        not_cons = []
        for cn in controlnets:
            if (
                cn.model_pattern
                + "_"
                + str(cn.type_of_controlnet)
                + "_"
                + str(cn.strength)
                in existing_controlnets
            ):
                cons.append(cn)
            else:
                not_cons.append(cn)

        item.controlnets = [asdict(cn) for cn in cons]

        for v in not_cons:
            if os.path.exists(v.image_path):
                os.remove(v.image_path)

    else:
        item.controlnets = []

    await item.save()


async def list_items(group_id: int) -> list[ItemOutput]:
    recs = await ItemRecord.filter(group_id=group_id)
    outs = []
    for rec in recs:
        io = serialize_item(rec)
        outs.append(io)
    return outs


async def list_items_paginated(
    group_id: int,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedOutput:
    offset = (page - 1) * page_size

    total = await ItemRecord.filter(group_id=group_id).count()
    items = (
        await ItemRecord.filter(group_id=group_id).offset(offset).limit(page_size).all()
    )

    return PaginatedOutput(
        items=[serialize_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


async def add_civitai_lora_as_item(
    cfg: Config,
    model: CivitaiLora,
    group_id: int,
    comfyui_path: str,
    comfyui_lora_subfolder_name: str,
):
    if cfg.civitai_api_token is None:
        raise Exception(
            "can't create group of LoRAs from Civitai if 'civitai_api_token' is missing from configurations"
        )

    if cfg.civitai_lora_path is None:
        raise Exception(
            "can't create group of LoRAs from Civitai if 'civitai_lora_path' is missing from configurations"
        )

    civitai_metadata = await lora_downloader.download_lora_from_civitai(
        model.model_id,
        cfg.civitai_lora_path,
        cfg.civitai_api_token,
        cfg.civitai_host,
    )
    print("civitai metadata", civitai_metadata)
    file_name = str(model.model_id) + ".safetensors"
    model_path = os.path.abspath(os.path.join(cfg.civitai_lora_path, file_name))

    lora_downloader.copy_lora_to_comfyui(
        model_path, comfyui_path, comfyui_lora_subfolder_name
    )

    lora_dict = asdict(
        Lora(
            name=os.path.join(comfyui_lora_subfolder_name, file_name),
            strength_clip=model.model_clip,
            strength_model=model.model_strength,
        )
    )
    lora_ls = [lora_dict]
    lora_str = json.dumps(lora_ls)

    positive_prompt = ""
    if "trigger_words" in civitai_metadata.keys():
        for v in civitai_metadata["trigger_words"]:
            positive_prompt += v + "\n\n"

    item_input = ItemInput(
        group_id=group_id,
        name=civitai_metadata["model_name"],
        code_name=str(model.model_id),
        positive_prompt=positive_prompt,
        negative_prompt="",
        lora=lora_str,
        controlnets=[],
        coordinated_regions=None,
        ipadapter=None,
        mask_region_reference_image=None,
        generator_output_type=None,
        generator_output_attributes=None,
        thumbnail_image=None,
    )
    await add_item(cfg, item_input)

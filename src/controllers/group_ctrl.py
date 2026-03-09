import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict

import aiohttp

from src.controllers.common import delete_item_files
from src.controllers.ctrl_types import (
    CivitaiLora,
    GroupInput,
    GroupOutput,
    ItemInput,
    Lora,
    ServerOutput,
)
from src.controllers.item_ctrl import add_item
from src.controllers.serializers import serialize_group
from src.core.config import Config
from src.core.utils import lora_downloader
from src.db.records import GroupRecord, ItemRecord


async def add_group(conf: Config, input: GroupInput) -> GroupOutput:
    thumbnail_path = None
    if input.thumbnail_image is not None:
        image_filename = str(uuid.uuid4()) + "_" + input.thumbnail_image.name
        thumbnail_path = os.path.join(conf.thumbnails_path, image_filename)
        await input.thumbnail_image.save(thumbnail_path)

    group = await GroupRecord.create(
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

    return serialize_group(group)


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
            lora_list=None,
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


async def add_group_of_loras_civitai(
    cfg: Config,
    models: list[CivitaiLora],
    input: GroupInput,
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

    group = await add_group(cfg, input)

    for model in models:
        civitai_metadata = await lora_downloader.download_lora_from_civitai(
            model.model_id, cfg.civitai_lora_path, cfg.civitai_api_token
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
            group_id=group.id,
            name=civitai_metadata["model_name"],
            code_name=str(model.model_id),
            positive_prompt=positive_prompt,
            negative_prompt="",
            lora=lora_str,
            controlnets=[],
            coordinated_regions=None,
            ipadapter=None,
            mask_region_reference_image=None,
            thumbnail_image=None,
        )
        await add_item(cfg, item_input)
        await asyncio.sleep(15)

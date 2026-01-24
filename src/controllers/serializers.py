import json
import os

from src.controllers.ctrl_types import (
    FixerOutput,
    GroupOutput,
    ItemIPAdapterOutput,
    ItemOutput,
    JobOutput,
)
from src.db.records import FixerRecord, GroupRecord, ItemRecord, JobRecord
from src.db.records.item_rec import IPAdapter, MaskRegionImages
from src.db.records.job_rec import RegionPrompt


def serialize_group(rec: GroupRecord) -> GroupOutput:
    show_thumbnail_image = None
    if rec.thumbnail_image is not None:
        show_thumbnail_image = (
            f"/thumbnails_path/{os.path.basename(rec.thumbnail_image)}"
        )

    return GroupOutput(
        id=rec.id,
        name=rec.name,
        description=rec.description,
        code_name=rec.code_name,
        category_id=rec.category_id,
        use_lora=rec.use_lora,
        use_controlnet=rec.use_controlnet,
        use_ip_adapter=rec.use_ip_adapter,
        use_mask_region=rec.use_mask_region,
        use_coordinates_region=rec.use_coordinates_region,
        thumbnail_image=rec.thumbnail_image,
        show_thumbnail_image=show_thumbnail_image,
    )


def serialize_job(rec: JobRecord) -> JobOutput:
    region_prompts = None
    if rec.region_prompts is not None:
        region_prompts = {}
        for k, p in rec.region_prompts.items():
            region_prompts[k] = RegionPrompt(**p)

    return JobOutput(
        id=rec.id,
        project_id=rec.project_id,
        command_id=rec.command_id,
        group_item_id_list=rec.group_item_id_list,
        code_str=rec.code_str,
        server_code_name=rec.server_code_name,
        server_host=rec.server_host,
        status=rec.status,
        generator_code_name=rec.generator_code_name,
        fixer_code_name=rec.fixer_code_name,
        comfyui_prompt_id=rec.comfyui_prompt_id,
        prompt_positive=rec.prompt_positive,
        prompt_negative=rec.prompt_negative,
        region_prompts=region_prompts,
        reference_controlnet_img=rec.reference_controlnet_img,
        ipadapter_list=rec.ipadapter_list,
        lora_list=rec.lora_list,
        result_img=rec.result_img,
        show_result_img=f"/result_path/{os.path.basename(rec.result_img)}",
    )


def serialize_fixer(rec: FixerRecord) -> FixerOutput:
    return FixerOutput(
        id=rec.id,
        name=rec.name,
        code_name=rec.code_name,
        positive_prompt=rec.positive_prompt,
        negative_prompt=rec.negative_prompt,
        positive_prompt_title=rec.positive_prompt_title,
        negative_prompt_title=rec.negative_prompt_title,
        load_image_title=rec.load_image_title,
        save_image_title=rec.save_image_title,
        workflow_json=rec.workflow_json,
    )


def serialize_item(rec: ItemRecord) -> ItemOutput:
    lora = None
    if rec.lora is not None:
        lora = json.dumps(rec.lora)

    show_controlnet_reference_image = None
    if rec.controlnet_reference_image is not None:
        show_controlnet_reference_image = f"/controlnet_references_path/{os.path.basename(rec.controlnet_reference_image)}"

    ipadapter: ItemIPAdapterOutput | None = None
    if rec.ipadapter is not None:
        item_ipadapter = IPAdapter(**rec.ipadapter)
        show_ipadapter_reference_image = (
            f"/ipadapter_references_path/{os.path.basename(item_ipadapter.image_file)}"
        )
        ipadapter = ItemIPAdapterOutput(
            reference_image=item_ipadapter.image_file,
            show_reference_image=show_ipadapter_reference_image,
            weight=item_ipadapter.weight,
            weight_type=item_ipadapter.weight_type,
            start_at=item_ipadapter.start_at,
            end_at=item_ipadapter.end_at,
            clip_vision_model=item_ipadapter.clip_vision_model,
            model_name=item_ipadapter.model_name,
        )

    show_thumbnail_image = None
    if rec.thumbnail_image is not None:
        show_thumbnail_image = (
            f"/thumbnails_path/{os.path.basename(rec.thumbnail_image)}"
        )

    mask_region_images = None
    mask_region_images_keys = None
    if rec.mask_region_images is not None:
        mask_region_images = MaskRegionImages(**rec.mask_region_images)
        mask_region_images_keys = f"{list(mask_region_images.mask_files.keys())}"

    coordinated_regions = None
    coordinated_region_keys = None
    if rec.coordinated_regions is not None:
        coordinated_regions = json.dumps(rec.coordinated_regions)
        coordinated_region_keys = (
            f"{list(map(lambda x: x['keyword'], rec.coordinated_regions))}"
        )

    io = ItemOutput(
        id=rec.id,
        group_id=rec.group_id,
        name=rec.name,
        code_name=rec.code_name,
        positive_prompt=rec.positive_prompt,
        negative_prompt=rec.negative_prompt,
        lora=lora,
        coordinated_regions=coordinated_regions,
        coordinated_region_keys=coordinated_region_keys,
        controlnet_reference_image=rec.controlnet_reference_image,
        show_controlnet_reference_image=show_controlnet_reference_image,
        ipadapter=ipadapter,
        mask_region_images=mask_region_images,
        mask_region_images_keys=mask_region_images_keys,
        thumbnail_image=rec.thumbnail_image,
        show_thumbnail_image=show_thumbnail_image,
    )

    return io

import json
import os

from yet_another_comfy_client import YetAnotherComfyClient

from src.controllers.ctrl_types import (
    CategoryOutput,
    CommandOutput,
    ControlNetConfig,
    FixerOutput,
    GeneratorOutput,
    GeneratorOutputType,
    GroupOutput,
    ImageAttributes,
    IPAdapter,
    ItemIPAdapterOutput,
    ItemOutput,
    JobOutput,
    JobStatus,
    MaskRegionImages,
    ProjectOutput,
    RegionPrompt,
    ServerOutput,
    StatusEnum,
    ThreeDAttributes,
    VideoAttributes,
)
from src.db.records import (
    CategoryRecord,
    CommandRecord,
    FixerRecord,
    GeneratorRecord,
    GroupRecord,
    ItemRecord,
    JobRecord,
    ProjectRecord,
)
from src.db.records.server_rec import ServerRecord


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
        use_type_attributes=rec.use_type_attributes,
        thumbnail_image=rec.thumbnail_image,
        show_thumbnail_image=show_thumbnail_image,
    )


def serialize_category(rec: CategoryRecord) -> CategoryOutput:
    return CategoryOutput(
        id=rec.id,
        name=rec.name,
    )


def serialize_project(rec: ProjectRecord) -> ProjectOutput:
    return ProjectOutput(
        id=rec.id,
        name=rec.name,
    )


async def serialize_command(rec: CommandRecord) -> CommandOutput:
    total_jobs = await JobRecord.filter(command_id=rec.id).count()
    finished_jobs = await JobRecord.filter(
        command_id=rec.id, status=JobStatus.FINISHED
    ).count()

    return CommandOutput(
        id=rec.id,
        project_id=rec.project_id,
        order=rec.order,
        command_code=rec.command_code,
        command_json=rec.command_json,
        total_jobs=total_jobs,
        finished_jobs=finished_jobs,
    )


async def serialize_server(rec: ServerRecord) -> ServerOutput:
    client = YetAnotherComfyClient(rec.host)
    status = StatusEnum.ONLINE
    try:
        await client.get_history()
    except Exception:
        status = StatusEnum.OFFLINE

    return ServerOutput(
        id=rec.id,
        name=rec.name,
        host=rec.host,
        is_local=rec.is_local,
        code_name=rec.code_name,
        status=status,
    )


def serialize_generator(gen: GeneratorRecord) -> GeneratorOutput:
    attrs = None
    match gen.output_type:
        case GeneratorOutputType.IMAGE:
            attrs = ImageAttributes(**gen.output_attributes)
        case GeneratorOutputType.VIDEO:
            attrs = VideoAttributes(**gen.output_attributes)
        case GeneratorOutputType.THREE_D:
            attrs = ThreeDAttributes(**gen.output_attributes)

    return GeneratorOutput(
        id=gen.id,
        name=gen.name,
        code_name=gen.code_name,
        workflow_json=gen.workflow_json,
        positive_prompt_title=gen.positive_prompt_title,
        negative_prompt_title=gen.negative_prompt_title,
        output_type=gen.output_type,
        output_attributes=attrs,
        output_node_class_type=gen.output_node_class_type,
        output_node_title=gen.output_node_title,
        has_random_seed=gen.has_random_seed,
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
        generator_output_type=rec.generator_output_type,
        generator_output_attributes=rec.generator_output_attributes,
        fixer_code_name=rec.fixer_code_name,
        comfyui_prompt_id=rec.comfyui_prompt_id,
        prompt_positive=rec.prompt_positive,
        prompt_negative=rec.prompt_negative,
        region_prompts=region_prompts,
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
    if rec.lora_list is not None:
        lora = json.dumps(rec.lora_list)

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

    controlnets = []
    if rec.controlnets is not None:
        for v in rec.controlnets:
            controlnets.append(
                ControlNetConfig(
                    type_of_controlnet=v["type_of_controlnet"],
                    image_path=v["image_path"],
                    is_reference=v["is_reference"],
                    model_pattern=v["model_pattern"],
                    strength=v["strength"],
                )
            )

    generator_output_type = None
    generator_output_attributes = None
    if rec.output_type is not None and rec.output_type_attributes is not None:
        generator_output_type = rec.output_type
        generator_output_attributes = json.dumps(rec.output_type_attributes)

    io = ItemOutput(
        id=rec.id,
        group_id=rec.group_id,
        name=rec.name,
        code_name=rec.code_name,
        positive_prompt=rec.positive_prompt,
        negative_prompt=rec.negative_prompt,
        lora=lora,
        controlnets=controlnets,
        coordinated_regions=coordinated_regions,
        coordinated_region_keys=coordinated_region_keys,
        ipadapter=ipadapter,
        mask_region_images=mask_region_images,
        mask_region_images_keys=mask_region_images_keys,
        generator_output_type=generator_output_type,
        generator_output_attributes=generator_output_attributes,
        thumbnail_image=rec.thumbnail_image,
        show_thumbnail_image=show_thumbnail_image,
    )

    return io

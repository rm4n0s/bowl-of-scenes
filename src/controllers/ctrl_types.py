import enum
import os
from dataclasses import dataclass
from typing import Any

from nicegui.elements.upload_files import FileUpload
from yet_another_comfy_client import YetAnotherComfyClient

from src.db.records import FixerRecord, GroupRecord
from src.db.records.item_rec import ColorCodeImages
from src.db.records.job_rec import ColorCodedPrompt, JobRecord, JobStatus


@dataclass
class CategoryInput:
    name: str


@dataclass
class CategoryOutput:
    id: int
    name: str


@dataclass
class GroupInput:
    name: str
    description: str
    code_name: str
    category_id: int
    use_lora: bool
    use_controlnet: bool
    use_ip_adapter: bool
    use_color_coded_region: bool
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
    use_color_coded_region: bool
    thumbnail_image: str | None
    show_thumbnail_image: str | None


@dataclass
class ItemInput:
    group_id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    lora: str | None
    controlnet_reference_image: FileUpload | None
    ipadapter_reference_image: FileUpload | None
    color_coded_reference_image: FileUpload | None
    thumbnail_image: FileUpload | None


@dataclass
class ItemOutput:
    id: int
    group_id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    lora: str | None
    controlnet_reference_image: str | None
    show_controlnet_reference_image: str | None
    ipadapter_reference_image: str | None
    show_ipadapter_reference_image: str | None
    color_coded_images: ColorCodeImages | None
    color_coded_images_keys: str | None
    thumbnail_image: str | None
    show_thumbnail_image: str | None


@dataclass
class ReplInput:
    generator_code_name: str
    server_code_name: str
    prompt_positive: str
    prompt_negative: str
    group_item_code_names: str
    reference_controlnet_img: FileUpload | None
    reference_ipadapter_img: FileUpload | None
    lora_list: str


@dataclass
class JobOutput:
    id: int
    project_id: int
    command_id: int
    group_item_id_list: list[dict[str, Any]]
    code_str: str
    server_code_name: str
    server_host: str
    status: JobStatus
    generator_code_name: str | None
    fixer_code_name: str | None
    comfyui_prompt_id: str | None
    prompt_positive: str
    prompt_negative: str
    reference_controlnet_img: str | None
    reference_ipadapter_img: str | None
    color_coded_prompts: dict[str, ColorCodedPrompt] | None
    lora_list: list[dict[str, Any]]
    result_img: str
    show_result_img: str


@dataclass
class ServerData:
    id: int
    host: str
    code_name: str
    client: YetAnotherComfyClient


@dataclass
class ProjectInput:
    name: str


@dataclass
class ProjectOutput:
    id: int
    name: str


class StatusEnum(enum.StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass
class ServerInput:
    name: str
    host: str
    code_name: str
    is_local: bool


@dataclass
class ServerOutput:
    id: int
    name: str
    host: str
    code_name: str
    is_local: bool
    status: StatusEnum


@dataclass
class GeneratorInput:
    name: str
    code_name: str
    workflow_json: dict[str, Any]
    positive_prompt_title: str | None
    negative_prompt_title: str | None
    load_image_ipadapter_title: str | None
    load_image_controlnet_title: str | None
    save_image_title: str


@dataclass
class GeneratorOutput:
    id: int
    name: str
    code_name: str
    workflow_json: dict[str, Any]
    positive_prompt_title: str | None
    negative_prompt_title: str | None
    load_image_ipadapter_title: str | None
    load_image_controlnet_title: str | None
    save_image_title: str


@dataclass
class FixerInput:
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    positive_prompt_title: str
    negative_prompt_title: str
    load_image_title: str
    save_image_title: str
    workflow_json: dict[str, Any]


@dataclass
class FixerOutput:
    id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    positive_prompt_title: str
    negative_prompt_title: str
    load_image_title: str
    save_image_title: str
    workflow_json: dict[str, Any]


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
        use_color_coded_region=rec.use_color_coded_region,
        thumbnail_image=rec.thumbnail_image,
        show_thumbnail_image=show_thumbnail_image,
    )


def serialize_job(rec: JobRecord) -> JobOutput:
    color_coded_prompts = None
    if rec.color_coded_prompts is not None:
        color_coded_prompts = {}
        for k, p in rec.color_coded_prompts.items():
            color_coded_prompts[k] = ColorCodedPrompt(**p)

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
        color_coded_prompts=color_coded_prompts,
        reference_controlnet_img=rec.reference_controlnet_img,
        reference_ipadapter_img=rec.reference_ipadapter_img,
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

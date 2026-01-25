import enum
import os
from dataclasses import dataclass
from typing import Any

from nicegui.elements.upload_files import FileUpload
from yet_another_comfy_client import YetAnotherComfyClient

from src.db.records import FixerRecord, GroupRecord
from src.db.records.item_rec import MaskRegionImages
from src.db.records.job_rec import JobRecord, JobStatus, RegionPrompt


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
    use_mask_region: bool
    use_coordinates_region: bool
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
    use_mask_region: bool
    use_coordinates_region: bool
    thumbnail_image: str | None
    show_thumbnail_image: str | None


@dataclass
class ItemIPAdapterInput:
    reference_image: FileUpload
    weight: float
    weight_type: str
    start_at: float
    end_at: float
    clip_vision_model: str
    model_name: str


@dataclass
class ItemIPAdapterOutput:
    reference_image: str
    show_reference_image: str
    weight: float
    weight_type: str
    start_at: float
    end_at: float
    clip_vision_model: str
    model_name: str


@dataclass
class ItemInput:
    group_id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    lora: str | None
    coordinated_regions: str | None
    controlnet_reference_image: FileUpload | None
    ipadapter: ItemIPAdapterInput | None
    mask_region_reference_image: FileUpload | None
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
    coordinated_regions: str | None
    coordinated_region_keys: str | None
    controlnet_reference_image: str | None
    show_controlnet_reference_image: str | None
    ipadapter: ItemIPAdapterOutput | None
    mask_region_images: MaskRegionImages | None
    mask_region_images_keys: str | None
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
    ipadapter_list: list[dict[str, Any]]
    region_prompts: dict[str, RegionPrompt] | None
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

import enum
import os
from dataclasses import dataclass
from typing import Any

from nicegui.elements.upload_files import FileUpload
from yet_another_comfy_client import YetAnotherComfyClient

from src.db.records import GroupRecord
from src.db.records.job_rec import JobRecord, JobStatus


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
    thumbnail_image: str | None
    show_thumbnail_image: str | None


@dataclass
class ReplInput:
    workflow_code_name: str
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
    workflow_code_name: str
    comfyui_prompt_id: str | None
    prompt_positive: str
    prompt_negative: str
    reference_controlnet_img: str | None
    reference_ipadapter_img: str | None
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
class WorkflowInput:
    name: str
    code_name: str
    workflow_json: dict[str, Any]
    positive_prompt_title: str | None
    negative_prompt_title: str | None
    load_image_ipadapter_title: str | None
    load_image_controlnet_title: str | None
    save_image_title: str


@dataclass
class WorkflowOutput:
    id: int
    name: str
    code_name: str
    workflow_json: dict[str, Any]
    positive_prompt_title: str | None
    negative_prompt_title: str | None
    load_image_ipadapter_title: str | None
    load_image_controlnet_title: str | None
    save_image_title: str


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
        thumbnail_image=rec.thumbnail_image,
        show_thumbnail_image=show_thumbnail_image,
    )


def serialize_job(rec: JobRecord) -> JobOutput:
    return JobOutput(
        id=rec.id,
        project_id=rec.project_id,
        command_id=rec.command_id,
        group_item_id_list=rec.group_item_id_list,
        code_str=rec.code_str,
        server_code_name=rec.server_code_name,
        server_host=rec.server_host,
        status=rec.status,
        workflow_code_name=rec.workflow_code_name,
        comfyui_prompt_id=rec.comfyui_prompt_id,
        prompt_positive=rec.prompt_positive,
        prompt_negative=rec.prompt_negative,
        reference_controlnet_img=rec.reference_controlnet_img,
        reference_ipadapter_img=rec.reference_ipadapter_img,
        lora_list=rec.lora_list,
        result_img=rec.result_img,
        show_result_img=f"/result_path/{os.path.basename(rec.result_img)}",
    )

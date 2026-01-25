import enum
from dataclasses import dataclass
from typing import Any

from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class JobStatus(enum.StrEnum):
    WAITING = "waiting"
    PROCESSING = "processing"
    FINISHED = "finished"


@dataclass
class CoordinatedRegion:
    width: int
    height: int
    x: int
    y: int


@dataclass
class RegionPrompt:
    keyword: str
    mask_file: str | None
    coordinates: CoordinatedRegion | None
    prompt: str


class JobRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    project_id = fields.IntField()
    command_id = fields.IntField()
    group_item_id_list = fields.JSONField()
    code_str = fields.TextField()
    server_code_name = fields.CharField(max_length=100)
    server_host = fields.CharField(max_length=100)
    status = fields.CharEnumField(enum_type=JobStatus, default=JobStatus.WAITING)
    generator_code_name = fields.CharField(max_length=100, null=True)
    fixer_code_name = fields.CharField(max_length=100, null=True)
    fix_job_id = fields.IntField(null=True)
    comfyui_prompt_id = fields.CharField(max_length=200, null=True, default=None)
    prompt_positive = fields.TextField()
    prompt_negative = fields.TextField()
    region_prompts = fields.JSONField(
        null=True, default=None
    )  # dict[str, RegionPrompt]
    reference_controlnet_img = fields.TextField(null=True)
    ipadapter_list = fields.JSONField(null=True)
    lora_list = fields.JSONField(null=True)
    result_img = fields.TextField()

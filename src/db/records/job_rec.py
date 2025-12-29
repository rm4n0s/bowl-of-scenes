import enum

from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class JobStatus(enum.StrEnum):
    WAITING = "waiting"
    PROCESSING = "processing"
    FINISHED = "finished"


class JobRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    project_id = fields.IntField()
    command_id = fields.IntField()
    group_item_id_list = fields.JSONField()
    code_str = fields.TextField()
    server_code_name = fields.CharField(max_length=100)
    server_host = fields.CharField(max_length=100)
    status = fields.CharEnumField(enum_type=JobStatus, default=JobStatus.WAITING)
    workflow_code_name = fields.CharField(max_length=100)
    comfyui_prompt_id = fields.CharField(max_length=200, null=True, default=None)
    prompt_positive = fields.TextField()
    prompt_negative = fields.TextField()
    reference_controlnet_img = fields.TextField(null=True)
    reference_ipadapter_img = fields.TextField(null=True)
    lora_list = fields.JSONField(null=True)
    result_img = fields.TextField()

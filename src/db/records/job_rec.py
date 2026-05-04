from tortoise import fields
from tortoise.models import Model

from src.controllers.ctrl_types import GeneratorOutputType, JobStatus
from src.db.records.common import TimestampMixin


class JobRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    project_id = fields.IntField()
    command_id = fields.IntField()
    group_item_id_list = fields.JSONField()  # list[{group_id, item_id}]
    code_str = fields.TextField()
    server_code_name = fields.CharField(max_length=100)
    server_host = fields.CharField(max_length=100)
    status = fields.CharEnumField(enum_type=JobStatus, default=JobStatus.IDLE)
    generator_code_name = fields.CharField(max_length=100, null=True)
    generator_output_type = fields.CharEnumField(
        enum_type=GeneratorOutputType, null=True
    )
    generator_output_attributes = fields.JSONField(null=True)
    comfyui_prompt_id = fields.CharField(max_length=200, null=True, default=None)
    prompt_positive = fields.TextField()
    prompt_negative = fields.TextField()
    controlnets = fields.JSONField(null=True)  # list[ControlNetConfig]
    region_prompts = fields.JSONField(
        null=True, default=None
    )  # dict[str, RegionPrompt]
    ipadapter_list = fields.JSONField(null=True)
    lora_list = fields.JSONField(null=True)
    result_img = fields.TextField()
    is_last = fields.BooleanField(default=False)  # it is the last job of a command
    error = fields.TextField(null=True, default=None)
    traceback = fields.TextField(null=True, default=None)
    total_fixers = fields.JSONField(default=[])  # list[FixerRecord.ID]
    finished_fixers = fields.JSONField(default=[])  # list[FixerRecord.ID]
    is_generated = fields.BooleanField(default=False)
    is_fixed = fields.BooleanField(default=False)

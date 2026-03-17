from tortoise import fields
from tortoise.models import Model

from src.controllers.ctrl_types import GeneratorOutputType
from src.db.records.common import TimestampMixin


class GeneratorRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    code_name = fields.CharField(unique=True, max_length=100)
    positive_prompt_title = fields.TextField(null=True)
    negative_prompt_title = fields.TextField(null=True)
    output_type = fields.CharEnumField(enum_type=GeneratorOutputType)
    # ImageAttributes | VideoAttributes | ThreeDAttributes | None
    output_attributes = fields.JSONField(null=True)
    output_node_class_type = fields.CharField(max_length=100)
    output_node_title = fields.CharField(max_length=100)

    has_random_seed = fields.BooleanField(default=False)
    workflow_json = fields.JSONField()

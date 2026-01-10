from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class FixerRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    code_name = fields.CharField(unique=True, max_length=100)
    positive_prompt = fields.TextField(null=True)
    negative_prompt = fields.TextField(null=True)
    positive_prompt_title = fields.TextField(null=True)
    negative_prompt_title = fields.TextField(null=True)
    load_image_title = fields.TextField()
    save_image_title = fields.TextField()
    workflow_json = fields.JSONField()

from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class ItemRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    group_id = fields.IntField()
    name = fields.CharField(max_length=100)
    code_name = fields.CharField(max_length=100)
    positive_prompt = fields.TextField()
    negative_prompt = fields.TextField()
    lora = fields.JSONField(null=True)
    controlnet_reference_image = fields.TextField(null=True)
    ipadapter_reference_image = fields.TextField(null=True)
    thumbnail_image = fields.TextField(null=True)

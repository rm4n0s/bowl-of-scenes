from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class ResultRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    project_id = fields.IntField()
    process_id = fields.IntField()
    code_json = fields.JSONField(null=True)
    image_path = fields.TextField()

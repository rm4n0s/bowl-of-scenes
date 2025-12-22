from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class ProcessRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    project_id = fields.IntField()
    order_id = fields.IntField()
    code_json = fields.JSONField()

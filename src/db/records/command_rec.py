from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class CommandRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    project_id = fields.IntField()
    order = fields.IntField()
    command_code = fields.TextField()
    command_json = fields.JSONField()

from tortoise import fields
from tortoise.models import Model

from src.controllers.ctrl_types import JobStatus
from src.db.records.common import TimestampMixin


class CommandRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    project_id = fields.IntField()
    order = fields.IntField()
    status = fields.CharEnumField(enum_type=JobStatus, default=JobStatus.IDLE)
    name = fields.CharField(max_length=100)
    description = fields.TextField()
    command_code = fields.TextField()
    command_json = fields.JSONField()

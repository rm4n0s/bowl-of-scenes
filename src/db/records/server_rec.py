from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class ServerRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    host = fields.CharField(max_length=100)
    code_name = fields.CharField(unique=True, max_length=100)
    is_local = fields.BooleanField()

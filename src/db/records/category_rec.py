from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class CategoryRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)

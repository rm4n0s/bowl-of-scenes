from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class GroupRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    # inside_group_id = fields.IntField(null=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField()
    code_name = fields.CharField(unique=True, max_length=100)
    category_id = fields.IntField(null=True)
    use_controlnet = fields.BooleanField()
    use_ip_adapter = fields.BooleanField()
    thumbnail_image = fields.TextField(null=True)

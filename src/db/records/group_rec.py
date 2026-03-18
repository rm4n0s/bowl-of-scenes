from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class GroupRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=300)
    description = fields.TextField()
    code_name = fields.CharField(unique=True, max_length=100)
    category_id = fields.IntField(null=True)
    use_controlnet = fields.BooleanField(default=False)
    use_ip_adapter = fields.BooleanField(default=False)
    use_mask_region = fields.BooleanField(default=False)
    use_type_attributes = fields.BooleanField(default=False)
    use_coordinates_region = fields.BooleanField(default=False)
    use_lora = fields.BooleanField(default=False)
    thumbnail_image = fields.TextField(null=True)

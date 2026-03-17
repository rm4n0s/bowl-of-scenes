from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


class ItemRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    group_id = fields.IntField()
    name = fields.CharField(max_length=300)
    code_name = fields.CharField(max_length=100)
    positive_prompt = fields.TextField()
    negative_prompt = fields.TextField()
    lora_list = fields.JSONField(null=True)  # list[Lora]
    ipadapter = fields.JSONField(null=True)  # IPAdapter
    controlnets = fields.JSONField(null=True)  # list[ControlNetConfig]
    mask_region_images = fields.JSONField(null=True)  # MaskRegionImages
    coordinated_regions = fields.JSONField(null=True)  # list[CoordinatedRegionKeyword]
    thumbnail_image = fields.TextField(null=True)

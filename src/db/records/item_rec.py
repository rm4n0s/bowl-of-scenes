from tortoise import fields
from tortoise.models import Model

from src.controllers.ctrl_types import GeneratorOutputType
from src.db.records.common import TimestampMixin


class ItemRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    group_id = fields.IntField()
    name = fields.CharField(max_length=300)
    code_name = fields.CharField(max_length=100)
    positive_prompt = fields.TextField()
    negative_prompt = fields.TextField()
    lora_list = fields.JSONField(null=True, default=None)  # list[Lora]
    ipadapter = fields.JSONField(null=True, default=None)  # IPAdapter
    controlnets = fields.JSONField(null=True, default=None)  # list[ControlNetConfig]
    mask_region_images = fields.JSONField(null=True, default=None)  # MaskRegionImages
    # list[CoordinatedRegionKeyword]
    coordinated_regions = fields.JSONField(null=True, default=None)
    output_type = fields.CharEnumField(
        enum_type=GeneratorOutputType, null=True, default=None
    )
    # ImageAttributes | VideoAttributes | ThreeDAttributes | None
    output_type_attributes = fields.JSONField(null=True, default=None)
    thumbnail_image = fields.TextField(null=True, default=None)

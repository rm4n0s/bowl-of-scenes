from dataclasses import dataclass

from tortoise import fields
from tortoise.models import Model

from src.db.records.common import TimestampMixin


@dataclass
class MaskRegionImages:
    reference_path: str
    folder_path: str
    mask_files: dict[str, str]


@dataclass
class CoordinatedRegionKeyword:
    keyword: str
    width: int
    height: int
    x: int
    y: int


@dataclass
class IPAdapter:
    image_file: str
    weight: float
    weight_type: str
    start_at: float
    end_at: float
    clip_vision_model: str
    model_name: str


class ItemRecord(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    group_id = fields.IntField()
    name = fields.CharField(max_length=100)
    code_name = fields.CharField(max_length=100)
    positive_prompt = fields.TextField()
    negative_prompt = fields.TextField()
    lora = fields.JSONField(null=True)
    controlnet_reference_image = fields.TextField(null=True)
    ipadapter = fields.JSONField(null=True)
    mask_region_images = fields.JSONField(null=True)
    coordinated_regions = fields.JSONField(null=True)
    thumbnail_image = fields.TextField(null=True)

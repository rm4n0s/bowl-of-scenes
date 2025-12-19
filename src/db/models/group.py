# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: SSPL-1.0
#
from tortoise import fields
from tortoise.models import Model

from src.db.models.common import TimestampMixin


class Group(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    inside_group_id = fields.IntField(null=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField()
    code_name = fields.CharField(unique=True, max_length=100)
    category_id = fields.IntField(null=True)
    use_loras = fields.BooleanField()
    use_controlnet = fields.BooleanField()
    thumbnail_image = fields.TextField(null=True)

# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: SSPL-1.0
#
from tortoise import fields
from tortoise.models import Model

from src.db.models.common import TimestampMixin


class Item(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    group_id = fields.IntField()
    name = fields.CharField(max_length=100)
    code_name = fields.CharField(unique=True, max_length=100)
    positive_prompt = fields.TextField()
    negative_prompt = fields.TextField()
    lora_json = fields.JSONField(null=True)
    reference_image = fields.TextField(null=True)
    thumbnail_image = fields.TextField(null=True)

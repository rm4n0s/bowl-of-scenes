# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: SSPL-1.0
#
from tortoise import fields
from tortoise.models import Model

from src.db.models.common import TimestampMixin


class Server(TimestampMixin, Model):
    id = fields.IntField(primary_key=True)
    name = fields.TextField()
    host = fields.TextField()
    is_local = fields.BooleanField()

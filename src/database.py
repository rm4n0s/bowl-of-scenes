# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: SSPL-1.0

from tortoise import Tortoise


async def init_db(filepath: str) -> None:
    await Tortoise.init(
        db_url=f"sqlite://{filepath}",
        modules={
            "models": [
                "src.db.models",
            ],
        },
    )
    await Tortoise.generate_schemas()


async def close_db() -> None:
    await Tortoise.close_connections()

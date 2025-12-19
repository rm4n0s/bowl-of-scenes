# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: SSPL-1.0

from nicegui import app, ui

from src.database import close_db, init_db


async def initialize_db():
    filepath = ":memory:"
    await init_db(filepath)


@ui.page("/")
async def index():
    ui.label("Hello from bowl-of-scenes!")


def main():
    app.on_startup(initialize_db)
    app.on_shutdown(close_db)

    ui.run()
    print("Hello from bowl-of-scenes!")


main()

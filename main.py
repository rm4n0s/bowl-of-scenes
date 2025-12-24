# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: SSPL-1.0

import argparse
import os

from nicegui import app, ui

from src.controllers.category_ctrl import init_predefined_categories
from src.core.config import Config, read_config
from src.database import close_db, init_db
from src.pages import (
    categories_page,
    groups_page,
    home_page,
    items_page,
    servers_page,
    workflows_page,
)

# Initialize pages

GLOBAL_CONF: Config | None = None


async def initialize():
    assert GLOBAL_CONF
    os.makedirs(GLOBAL_CONF.controlnet_references_path, exist_ok=True)
    os.makedirs(GLOBAL_CONF.ipadapter_references_path, exist_ok=True)
    os.makedirs(GLOBAL_CONF.thumbnails_path, exist_ok=True)

    await init_db(GLOBAL_CONF.db_path)
    await init_predefined_categories()


def main():
    global GLOBAL_CONF
    parser = argparse.ArgumentParser(
        prog="Bowl Of Scenes",
        description="It is a server for generating images a batch of images based on combination of attributes",
    )

    _ = parser.add_argument(
        "--config", default="config.yaml", help="the configuration file"
    )
    args = parser.parse_args()
    config_path = args.config

    GLOBAL_CONF = read_config(config_path)

    app.on_startup(initialize)
    app.on_shutdown(close_db)
    home_page.init()
    servers_page.init()
    workflows_page.init()
    categories_page.init()
    groups_page.init(GLOBAL_CONF)
    items_page.init(GLOBAL_CONF)
    ui.run()
    print("Hello from bowl-of-scenes!")


main()

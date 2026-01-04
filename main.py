# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: SSPL-1.0

import argparse
import os

from nicegui import app, ui

from src.controllers.category_ctrl import init_predefined_categories
from src.controllers.manager_ctrl import Manager
from src.core.config import Config, read_config
from src.database import close_db, init_db
from src.pages import (
    categories_page,
    commands_page,
    groups_page,
    home_page,
    items_page,
    jobs_page,
    projects_page,
    servers_page,
    workflows_page,
)

# Initialize pages

GLOBAL_CONF: Config | None = None
GLOBAL_MANAGER: Manager | None


async def initialize():
    global GLOBAL_CONF
    global GLOBAL_MANAGER
    assert GLOBAL_CONF
    assert GLOBAL_MANAGER
    await GLOBAL_MANAGER.start_background_tasks()
    os.makedirs(GLOBAL_CONF.result_path, exist_ok=True)
    os.makedirs(GLOBAL_CONF.controlnet_references_path, exist_ok=True)
    os.makedirs(GLOBAL_CONF.ipadapter_references_path, exist_ok=True)
    os.makedirs(GLOBAL_CONF.thumbnails_path, exist_ok=True)

    await init_db(GLOBAL_CONF.db_path)
    await init_predefined_categories()


def main():
    global GLOBAL_CONF
    global GLOBAL_MANAGER
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
    GLOBAL_MANAGER = Manager(GLOBAL_CONF)

    app.on_startup(initialize)
    app.on_shutdown(close_db)

    app.add_static_files("/result_path", GLOBAL_CONF.result_path)
    app.add_static_files(
        "/controlnet_references_path", GLOBAL_CONF.controlnet_references_path
    )
    app.add_static_files(
        "/ipadapter_references_path", GLOBAL_CONF.ipadapter_references_path
    )
    app.add_static_files("/thumbnails_path", GLOBAL_CONF.thumbnails_path)
    home_page.init()
    servers_page.init()
    workflows_page.init()
    categories_page.init()
    projects_page.init()

    commands_page.init(GLOBAL_CONF, GLOBAL_MANAGER)
    jobs_page.init(GLOBAL_CONF, GLOBAL_MANAGER)
    groups_page.init(GLOBAL_CONF)
    items_page.init(GLOBAL_CONF)
    ui.run(title="Bowl of scenes", reload=False, show=False)


main()

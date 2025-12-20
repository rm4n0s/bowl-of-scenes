# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: SSPL-1.0

import argparse
import os

from nicegui import app, ui

from src.core.config import read_config
from src.database import close_db, init_db
from src.pages import home, servers

# Initialize pages


async def initialize():
    parser = argparse.ArgumentParser(
        prog="Bowl Of Scenes",
        description="It is a server for generating images a batch of images based on combination of attributes",
    )

    _ = parser.add_argument(
        "--config", default="config.yaml", help="the configuration file"
    )
    args = parser.parse_args()
    config_path = args.config

    config = read_config(config_path)
    os.makedirs(config.controlnet_references_path, exist_ok=True)
    os.makedirs(config.ipadapter_references_path, exist_ok=True)
    os.makedirs(config.thumbnails_path, exist_ok=True)

    await init_db(config.db_path)


home.init()
servers.init()


def main():
    app.on_startup(initialize)
    app.on_shutdown(close_db)

    ui.run()
    print("Hello from bowl-of-scenes!")


main()

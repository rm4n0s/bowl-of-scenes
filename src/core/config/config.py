# Copyright © 2025-2026 Emmanouil Ragiadakos
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

from mashumaro.mixins.yaml import DataClassYAMLMixin


@dataclass
class Config(DataClassYAMLMixin):
    db_path: str
    results_path: str
    references_path: str
    thumbnail_path: str


def read_config(filepath: str) -> Config:
    with open(filepath, "r") as file:
        yaml_content = file.read()
        config = Config.from_yaml(yaml_content)
        return config

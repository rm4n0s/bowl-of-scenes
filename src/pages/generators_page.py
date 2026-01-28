import json
from dataclasses import asdict
from typing import Any

from nicegui import ui
from nicegui.events import UploadEventArguments

from src.controllers.generator_ctrl import (
    GeneratorInput,
    add_generator,
    delete_generator,
    edit_generator,
    list_generators,
)
from src.core.utils import get_title_from_class_type
from src.core.utils.utils import get_title_from_class_type_that_contains
from src.pages.common.nav_menu import common_nav_menu


class GeneratorsPage:
    table: ui.table | None

    def __init__(self):
        self.items = []
        self.selected_item = None
        self.table = None

    async def load_items(self):
        gens = await list_generators()
        self.items = [asdict(gen) for gen in gens]
        if self.table:
            self.table.rows = self.items  # Assign new rows
            self.table.update()

    def show_create_dialog(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Create New Generator").classes("text-h6")

            name_input = ui.input("Name").props("outlined")
            code_name_input = ui.input("Code name").props("outlined")
            workflow_json: dict[str, Any] = {}
            positive_prompt_title_input = ui.input("Positive Prompt's title").props(
                "outlined"
            )
            negative_prompt_title_input = ui.input("Negative Prompt's title").props(
                "outlined"
            )
            save_image_title_input = ui.input("SaveImage's title").props("outlined")
            load_image_controlnet_title_input = ui.input(
                "LoadImage's title for ControlNet"
            ).props("outlined")

            async def handle_upload(event: UploadEventArguments):
                nonlocal workflow_json
                workflow_json = await event.file.json()
                save_image_titles = get_title_from_class_type(
                    workflow_json, "SaveImage"
                )
                if len(save_image_titles) > 0:
                    save_image_title_input.value = save_image_titles[
                        len(save_image_titles) - 1
                    ]

                load_image_titles = get_title_from_class_type(
                    workflow_json, "LoadImage"
                )

                for title in load_image_titles:
                    low_title = title.lower()
                    if "controlnet" in low_title:
                        load_image_controlnet_title_input.value = title

                prompt_titles = get_title_from_class_type_that_contains(
                    workflow_json, "TextEncode"
                )
                for title in prompt_titles:
                    low_title = title.lower()
                    if "positive" in low_title:
                        positive_prompt_title_input.value = title

                    if "negative" in low_title:
                        negative_prompt_title_input.value = title

            ui.label("Upload Workflow JSON").classes("text-h6")
            ui.upload(on_upload=lambda e: handle_upload(e), auto_upload=True).props(
                'accept=".json"'
            )

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Create",
                    on_click=lambda: self.handle_create(
                        dialog,
                        name_input.value,
                        code_name_input.value,
                        workflow_json,
                        positive_prompt_title_input.value,
                        negative_prompt_title_input.value,
                        load_image_controlnet_title_input.value,
                        save_image_title_input.value,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_create(
        self,
        dialog,
        name: str,
        code_name: str,
        workflow_json: dict[str, Any],
        positive_prompt_title: str,
        negative_prompt_title: str,
        load_image_controlnet_title: str,
        save_image_title: str,
    ):
        input = GeneratorInput(
            name=name,
            code_name=code_name,
            workflow_json=workflow_json,
            positive_prompt_title=positive_prompt_title,
            negative_prompt_title=negative_prompt_title,
            load_image_controlnet_title=load_image_controlnet_title,
            save_image_title=save_image_title,
        )

        await add_generator(input)
        await self.load_items()
        ui.notify("Generator created successfully", type="positive")
        dialog.close()

    def show_edit_dialog(self, item):
        with ui.dialog() as dialog, ui.card():
            ui.label("Edit Generator").classes("text-h6")

            name_input = ui.input("Name", value=item["name"]).props("outlined")
            code_name_input = ui.input("Code name", value=item["code_name"]).props(
                "outlined"
            )
            workflow_json_str = (
                ui.textarea(
                    "Generator's JSON file path",
                    value=json.dumps(item["workflow_json"], sort_keys=True, indent=4),
                )
                .classes("w-96")
                .props("outlined rows=15")
            )
            positive_prompt_title_input = ui.input(
                "Positive Prompt's title", value=item["positive_prompt_title"]
            ).props("outlined")
            negative_prompt_title_input = ui.input(
                "Negative Prompt's title", value=item["negative_prompt_title"]
            ).props("outlined")
            load_image_controlnet_title_input = ui.input(
                "LoadImage's for controlnet's title",
                value=item["load_image_controlnet_title"],
            ).props("outlined")
            save_image_title_input = ui.input(
                "SaveImage title", value=item["save_image_title"]
            ).props("outlined")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Update",
                    on_click=lambda: self.handle_update(
                        dialog,
                        item["id"],
                        name_input.value,
                        code_name_input.value,
                        workflow_json_str.value,
                        positive_prompt_title_input.value,
                        negative_prompt_title_input.value,
                        load_image_controlnet_title_input.value,
                        save_image_title_input.value,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_update(
        self,
        dialog,
        workflow_id,
        name: str,
        code_name: str,
        workflow_json_str: str,
        positive_prompt_title: str,
        negative_prompt_title: str,
        load_image_controlnet_title: str,
        save_image_title: str,
    ):
        workflow_json = json.loads(workflow_json_str)
        input = GeneratorInput(
            name=name,
            code_name=code_name,
            workflow_json=workflow_json,
            positive_prompt_title=positive_prompt_title,
            negative_prompt_title=negative_prompt_title,
            load_image_controlnet_title=load_image_controlnet_title,
            save_image_title=save_image_title,
        )

        await edit_generator(workflow_id, input)
        await self.load_items()
        ui.notify("Generator updated successfully", type="positive")
        dialog.close()

    def show_delete_dialog(self, item):
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete {item['name']}?").classes("text-h6")
            ui.label("This action cannot be undone.")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Delete", on_click=lambda: self.handle_delete(dialog, item["id"])
                ).props("color=negative")

        dialog.open()

    async def handle_delete(self, dialog, item_id):
        await delete_generator(item_id)
        await self.load_items()
        ui.notify("Generator deleted successfully", type="positive")
        dialog.close()

    async def render(self):
        """Render the CRUD page"""
        ui.label("Generator Management").classes("text-h4 q-mb-md")

        # Action buttons
        with ui.row().classes("q-mb-md"):
            ui.button(
                "Add Generator", icon="add", on_click=self.show_create_dialog
            ).props("color=primary")
            ui.button("Refresh", icon="refresh", on_click=self.load_items)

        @ui.refreshable
        async def table():
            await self.load_items()
            columns = [
                {"name": "id", "label": "ID", "field": "id", "align": "left"},
                {"name": "name", "label": "Name", "field": "name", "align": "left"},
                {
                    "name": "code_name",
                    "label": "Code Name",
                    "field": "code_name",
                    "align": "left",
                },
                {
                    "name": "actions",
                    "label": "Actions",
                    "field": "actions",
                    "align": "right",
                },
            ]
            self.table = ui.table(
                columns=columns, rows=self.items, row_key="id"
            ).classes("w-full")

            # Add action buttons to each row
            self.table.add_slot(
                "body-cell-actions",
                """
                <q-td :props="props">
                    <q-btn flat dense icon="edit" @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat dense icon="delete" color="negative" @click="$parent.$emit('delete', props.row)" />
                </q-td>
            """,
            )

            self.table.on("edit", lambda e: self.show_edit_dialog(e.args))
            self.table.on("delete", lambda e: self.show_delete_dialog(e.args))

        await table()


def init():
    @ui.page("/generators")
    async def page():
        ui.dark_mode().auto()
        page = GeneratorsPage()
        await common_nav_menu()
        await page.render()
        await page.load_items()

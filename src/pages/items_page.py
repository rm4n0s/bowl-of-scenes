from dataclasses import asdict

from fastapi import HTTPException
from nicegui import ui
from nicegui.elements.textarea import Textarea
from nicegui.elements.upload_files import FileUpload
from nicegui.events import MultiUploadEventArguments

from src.controllers.group_ctrl import GroupOutput, get_group
from src.controllers.item_ctrl import (
    ItemInput,
    add_item,
    delete_item,
    edit_item,
    list_items,
)
from src.core.config import Config
from src.pages.common.nav_menu import common_nav_menu


class ItemsPage:
    table: ui.table | None

    def __init__(self, conf: Config, group: GroupOutput):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.group = group

    async def load_items(self):
        ips = await list_items(self.group.id)
        self.items = [asdict(ip) for ip in ips]
        if self.table:
            self.table.rows = self.items  # Assign new rows
            self.table.update()

    async def show_create_dialog(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Create New Item").classes("text-h6")

            name_input = ui.input("Name").props("outlined")
            code_name_input = ui.input("Code Name").props("outlined")
            positive_prompt_input = ui.textarea("Positive prompt").props("outlined")
            negative_prompt_input = ui.textarea("Negative prompt").props("outlined")

            lora_input = None
            if self.group.use_lora:
                lora_input = ui.textarea(
                    "LoRA in JSON",
                    placeholder="""
{
   "name": "style_lora.safetensors",
   "strength_model": 0.7,
   "strength_clip": 0.7
}
                    """,
                ).props("outlined")

            ipadapter_reference_image_input = None
            if self.group.use_ip_adapter:

                async def handle_ipadapter_upload(event: MultiUploadEventArguments):
                    nonlocal ipadapter_reference_image_input
                    if event.files:
                        ipadapter_reference_image_input = event.files[0]

                ui.label("Upload IP Adapter image").classes("text-h6")
                ui.upload(
                    on_multi_upload=lambda e: handle_ipadapter_upload(e),
                    auto_upload=True,
                    max_files=1,
                ).props('accept="image/jpeg,image/png"')

            controlnet_reference_image_input = None
            if self.group.use_controlnet:

                async def handle_controlnet_upload(event: MultiUploadEventArguments):
                    nonlocal controlnet_reference_image_input
                    if event.files:
                        controlnet_reference_image_input = event.files[0]

                ui.label("Upload Controlnet image").classes("text-h6")
                ui.upload(
                    on_multi_upload=lambda e: handle_controlnet_upload(e),
                    auto_upload=True,
                    max_files=1,
                ).props('accept="image/jpeg,image/png"')

            thumbnail_image_input = None

            async def handle_thumbnail_upload(event: MultiUploadEventArguments):
                nonlocal thumbnail_image_input
                print("handle upload", event.files is not None)
                if event.files:
                    print("event files", len(event.files))
                    thumbnail_image_input = event.files[0]

            ui.label("Upload thumbnail image").classes("text-h6")
            ui.upload(
                on_multi_upload=lambda e: handle_thumbnail_upload(e),
                auto_upload=True,
                max_files=1,
            ).props('accept="image/jpeg,image/png"')

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Create",
                    on_click=lambda: self.handle_create(
                        dialog,
                        name_input.value,
                        code_name_input.value,
                        positive_prompt_input.value,
                        negative_prompt_input.value,
                        lora_input,
                        controlnet_reference_image_input,
                        ipadapter_reference_image_input,
                        thumbnail_image_input,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_create(
        self,
        dialog,
        name: str,
        code_name: str,
        positive_prompt: str,
        negative_prompt: str,
        lora_input: Textarea | None,
        controlnet_reference_image: FileUpload | None,
        ipadapter_reference_image: FileUpload | None,
        thumbnail_image: FileUpload | None,
    ):
        lora = None
        if lora_input is not None:
            if len(lora_input.value) > 0:
                lora = lora_input.value

        input = ItemInput(
            group_id=self.group.id,
            name=name,
            code_name=code_name,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            lora=lora,
            controlnet_reference_image=controlnet_reference_image,
            ipadapter_reference_image=ipadapter_reference_image,
            thumbnail_image=thumbnail_image,
        )

        await add_item(self.conf, input)
        await self.load_items()
        ui.notify("Item created successfully", type="positive")
        dialog.close()

    async def show_edit_dialog(self, item):
        with ui.dialog() as dialog, ui.card():
            ui.label("Edit Item").classes("text-h6")

            name_input = ui.input("Name", value=item["name"]).props("outlined")
            code_name_input = ui.input("Code Name", value=item["code_name"]).props(
                "outlined"
            )
            positive_prompt_input = ui.textarea(
                "Positive prompt", value=item["positive_prompt"]
            ).props("outlined")
            negative_prompt_input = ui.textarea(
                "Negative prompt", value=item["negative_prompt"]
            ).props("outlined")

            lora_input = None
            if self.group.use_lora:
                lora = ""
                if item["lora"] is not None:
                    lora = item["lora"]
                lora_input = ui.textarea("LoRA in JSON", value=lora).props("outlined")

            ipadapter_reference_image_input = None
            if self.group.use_ip_adapter:

                async def handle_ipadapter_upload(event: MultiUploadEventArguments):
                    nonlocal ipadapter_reference_image_input
                    if event.files:
                        ipadapter_reference_image_input = event.files[0]

                ui.label("Upload IP Adapter image").classes("text-h6")
                ui.upload(
                    on_multi_upload=lambda e: handle_ipadapter_upload(e),
                    auto_upload=True,
                    max_files=1,
                ).props('accept="image/jpeg,image/png"')

            controlnet_reference_image_input = None
            if self.group.use_controlnet:

                async def handle_controlnet_upload(event: MultiUploadEventArguments):
                    nonlocal controlnet_reference_image_input
                    if event.files:
                        controlnet_reference_image_input = event.files[0]

                ui.label("Upload Controlnet image").classes("text-h6")
                ui.upload(
                    on_multi_upload=lambda e: handle_controlnet_upload(e),
                    auto_upload=True,
                    max_files=1,
                ).props('accept="image/jpeg,image/png"')

            thumbnail_image_input = None

            async def handle_thumbnail_upload(event: MultiUploadEventArguments):
                nonlocal thumbnail_image_input
                print("handle upload", event.files is not None)
                if event.files:
                    print("event files", len(event.files))
                    thumbnail_image_input = event.files[0]

            ui.label("Upload thumbnail image").classes("text-h6")
            ui.upload(
                on_multi_upload=lambda e: handle_thumbnail_upload(e),
                auto_upload=True,
                max_files=1,
            ).props('accept="image/jpeg,image/png"')

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Update",
                    on_click=lambda: self.handle_update(
                        dialog,
                        item["id"],
                        name_input.value,
                        code_name_input.value,
                        positive_prompt_input.value,
                        negative_prompt_input.value,
                        lora_input,
                        controlnet_reference_image_input,
                        ipadapter_reference_image_input,
                        thumbnail_image_input,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_update(
        self,
        dialog,
        item_id,
        name: str,
        code_name: str,
        positive_prompt: str,
        negative_prompt: str,
        lora_input: Textarea | None,
        controlnet_reference_image: FileUpload | None,
        ipadapter_reference_image: FileUpload | None,
        thumbnail_image: FileUpload | None,
    ):
        lora = None
        if lora_input is not None:
            if len(lora_input.value) > 0:
                lora = lora_input.value

        input = ItemInput(
            group_id=self.group.id,
            name=name,
            code_name=code_name,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            lora=lora,
            controlnet_reference_image=controlnet_reference_image,
            ipadapter_reference_image=ipadapter_reference_image,
            thumbnail_image=thumbnail_image,
        )

        await edit_item(self.conf, item_id, input)
        await self.load_items()
        ui.notify("Item updated successfully", type="positive")
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
        await delete_item(item_id)
        await self.load_items()
        ui.notify("Item deleted successfully", type="positive")
        dialog.close()

    async def render(self):
        """Render the CRUD page"""
        ui.label("Items Management for " + self.group.name).classes("text-h4 q-mb-md")

        # Action buttons
        with ui.row().classes("q-mb-md"):
            ui.button("Add item", icon="add", on_click=self.show_create_dialog).props(
                "color=primary"
            )
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
                    "name": "positive_prompt",
                    "label": "Positive Prompt",
                    "field": "positive_prompt",
                    "align": "left",
                },
                {
                    "name": "negative_prompt",
                    "label": "Negative Prompt",
                    "field": "negative_prompt",
                    "align": "left",
                },
                {
                    "name": "show_controlnet_reference_image",
                    "label": "ControlNet image",
                    "field": "show_controlnet_reference_image",
                    "align": "left",
                },
                {
                    "name": "show_ipadapter_reference_image",
                    "label": "IPAdapter image",
                    "field": "show_ipadapter_reference_image",
                    "align": "left",
                },
                {
                    "name": "show_thumbnail_image",
                    "label": "Thumbnail image",
                    "field": "show_thumbnail_image",
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

            self.table.add_slot(
                "body-cell-show_thumbnail_image",
                """
                <q-td :props="props">
                                <img
                                    v-if="props.value"
                                    :src="props.value"
                                    style="width: 50px; height: 50px; object-fit: cover; cursor: pointer;"
                                >
                            </q-td>
                        """,
            )

            self.table.add_slot(
                "body-cell-show_ipadapter_reference_image",
                """
                <q-td :props="props">
                                <img
                                    v-if="props.value"
                                    :src="props.value"
                                    style="width: 50px; height: 50px; object-fit: cover; cursor: pointer;"
                                >
                            </q-td>
                        """,
            )

            self.table.add_slot(
                "body-cell-show_controlnet_reference_image",
                """
                <q-td :props="props">
                                <img
                                    v-if="props.value"
                                    :src="props.value"
                                    style="width: 50px; height: 50px; object-fit: cover; cursor: pointer;"
                                >
                            </q-td>
                        """,
            )

            # Add action buttons to each row
            self.table.add_slot(
                "body-cell-actions",
                """
                <q-td :props="props">
                    <q-btn flat dense icon="edit" class="q-mr-sm"  @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat dense icon="delete" class="q-mr-xl"  color="negative" @click="$parent.$emit('delete', props.row)" />
                </q-td>
            """,
            )

            self.table.on("edit", lambda e: self.show_edit_dialog(e.args))
            self.table.on("delete", lambda e: self.show_delete_dialog(e.args))

        await table()


def init(conf: Config):
    @ui.page("/groups/{group_id}/items")
    async def page(group_id: int):
        ui.dark_mode().auto()
        group = await get_group(group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        page = ItemsPage(conf, group)
        await common_nav_menu()
        await page.render()
        await page.load_items()

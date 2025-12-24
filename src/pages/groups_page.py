from dataclasses import asdict

from nicegui import ui
from nicegui.elements.upload_files import FileUpload
from nicegui.events import MultiUploadEventArguments, UploadEventArguments

from src.controllers.category_ctrl import list_categories
from src.controllers.group_ctrl import GroupInput, add_group, list_groups
from src.core.config import Config


class GroupsPage:
    table: ui.table | None

    def __init__(self, conf: Config):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf

    async def load_items(self):
        gps = await list_groups()
        gps_dicts = [asdict(gp) for gp in gps]
        self.items = gps_dicts
        if self.table:
            self.table.rows = self.items  # Assign new rows
            self.table.update()

    async def show_create_dialog(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Create New Group").classes("text-h6")
            categories = await list_categories()
            cat_dicts = {}
            for cat in categories:
                cat_dicts[cat.id] = cat.name

            name_input = ui.input("Name").props("outlined")
            description_input = ui.input("Description").props("outlined")
            code_name_input = ui.input("Code Name").props("outlined")
            category_id_input = ui.select(
                cat_dicts, label="Categories", value=categories[0].id
            )
            use_controlnet_input = ui.checkbox("Use ControlNet").props("outlined")
            use_ip_adapter_input = ui.checkbox("Use IP Adapter").props("outlined")
            thumbnail_image_input = None

            async def handle_upload(event: MultiUploadEventArguments):
                nonlocal thumbnail_image_input
                print("handle upload", event.files is not None)
                if event.files:
                    print("event files", len(event.files))
                    thumbnail_image_input = event.files[0]

            ui.label("Upload thumbnail image").classes("text-h6")
            ui.upload(
                on_multi_upload=lambda e: handle_upload(e),
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
                        description_input.value,
                        code_name_input.value,
                        category_id_input.value,  # pyright: ignore[reportArgumentType]
                        use_controlnet_input.value,
                        use_ip_adapter_input.value,
                        thumbnail_image_input,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_create(
        self,
        dialog,
        name: str,
        description: str,
        code_name: str,
        category_id: int,
        use_controlnet: bool,
        use_ip_adapter: bool,
        thumbnail_image: FileUpload | None,
    ):
        print("thumbnail_image uploaded", thumbnail_image is not None)
        input = GroupInput(
            name=name,
            description=description,
            code_name=code_name,
            category_id=category_id,
            use_controlnet=use_controlnet,
            use_ip_adapter=use_ip_adapter,
            thumbnail_image=thumbnail_image,
        )

        await add_group(self.conf, input)
        await self.load_items()
        ui.notify("Group created successfully", type="positive")
        dialog.close()

    async def show_edit_dialog(self, item):
        with ui.dialog() as dialog, ui.card():
            ui.label("Edit Group").classes("text-h6")
            categories = await list_categories()
            cat_dicts = {}
            for cat in categories:
                cat_dicts[cat.id] = cat.name

            name_input = ui.input("Name", value=item["name"]).props("outlined")
            description_input = ui.input("Description").props("outlined")
            code_name_input = ui.input("Code Name").props("outlined")
            category_id_input = ui.select(cat_dicts, value=categories[0].id)
            use_controlnet_input = ui.checkbox("Use ControlNet").props("outlined")
            use_ip_adapter_input = ui.checkbox("Use IP Adapter").props("outlined")
            thumbnail_image_input = None

            async def handle_upload(event: UploadEventArguments):
                nonlocal thumbnail_image_input
                thumbnail_image_input = event.file

            ui.label("Upload thumbnail image").classes("text-h6")
            ui.upload(on_upload=lambda e: handle_upload(e), auto_upload=True).props(
                'accept=".jpg,.png"'
            )

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Update",
                    on_click=lambda: self.handle_update(
                        dialog,
                        item["id"],
                        name_input.value,
                        description_input.value,
                        code_name_input.value,
                        category_id_input.value,  # pyright: ignore[reportArgumentType]
                        use_controlnet_input.value,
                        use_ip_adapter_input.value,
                        thumbnail_image_input,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_update(
        self,
        dialog,
        item_id,
        name: str,
        description: str,
        code_name: str,
        category_id: int,
        use_controlnet: bool,
        use_ip_adapter: bool,
        thumbnail_image: FileUpload | None,
    ):
        await self.load_items()
        ui.notify("Group updated successfully", type="positive")
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

    def redirect_to_items(self, item):
        ui.navigate.to(f"/groups/{item['id']}/items")

    async def handle_delete(self, dialog, item_id):
        # await self.delete_workflow(item_id)
        await self.load_items()
        ui.notify("Group deleted successfully", type="positive")
        dialog.close()

    async def render(self):
        """Render the CRUD page"""
        ui.label("Group Management").classes("text-h4 q-mb-md")

        # Action buttons
        with ui.row().classes("q-mb-md"):
            ui.button("Add group", icon="add", on_click=self.show_create_dialog).props(
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
                    "name": "category_id",
                    "label": "Category",
                    "field": "category_id",
                    "align": "left",
                },
                {
                    "name": "use_controlnet",
                    "label": "Uses ControlNet",
                    "field": "use_controlnet",
                    "align": "left",
                },
                {
                    "name": "use_ip_adapter",
                    "label": "Uses IP Adapter",
                    "field": "use_ip_adapter",
                    "align": "left",
                },
                {
                    "name": "thumbnail_image",
                    "label": "Thumbnail",
                    "field": "thumbnail_image",
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
                    <q-btn flat dense icon="edit" class="q-mr-sm"  @click="$parent.$emit('edit', props.row)" />
                    <q-btn flat dense icon="delete" class="q-mr-xl"  color="negative" @click="$parent.$emit('delete', props.row)" />
                    <q-btn flat dense icon="table"   @click="$parent.$emit('show_items', props.row)" />
                </q-td>
            """,
            )

            self.table.on("edit", lambda e: self.show_edit_dialog(e.args))
            self.table.on("delete", lambda e: self.show_delete_dialog(e.args))
            self.table.on("show_items", lambda e: self.redirect_to_items(e.args))

        await table()


def init(conf: Config):
    @ui.page("/groups")
    async def page():
        ui.dark_mode().auto()
        page = GroupsPage(conf)
        await page.render()
        await page.load_items()

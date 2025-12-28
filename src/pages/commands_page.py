from dataclasses import asdict

from fastapi import HTTPException
from nicegui import ui
from nicegui.elements.label import Label

from src.controllers.command_ctrl.command_ctrl import (
    CommandInput,
    add_command,
    delete_command,
    list_commands,
)
from src.controllers.project_ctrl import ProjectOutput, get_project
from src.core.config import Config


class CommandsPage:
    def __init__(self, conf: Config, project: ProjectOutput):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.project = project

    async def load_items(self):
        cmds = await list_commands(self.project.id)
        cmds_dicts = [asdict(cmd) for cmd in cmds]
        print("cmds", cmds_dicts)
        self.items = cmds_dicts
        if self.table:
            self.table.rows = self.items  # Assign new rows
            self.table.update()

    async def show_create_dialog(self):
        with ui.dialog() as dialog, ui.card():
            ui.label("Create New Item").classes("text-h6")

            code_input = ui.textarea("Code").props("outlined")
            error_label = ui.label("").classes("text-red-600")
            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Create",
                    on_click=lambda: self.handle_create(
                        dialog,
                        code_input.value,
                        error_label,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_create(self, dialog, code: str, error_label: Label):
        input = CommandInput(
            project_id=self.project.id,
            code=code,
        )

        errors = await add_command(input)
        if errors is not None:
            ui.notify("Command didn't created", type="negative")
            error_label.set_text(str(errors))
            return
        await self.load_items()
        ui.notify("Command created successfully", type="positive")
        dialog.close()

    async def show_edit_dialog(self, item):
        with ui.dialog() as dialog, ui.card():
            ui.label("Edit Command").classes("text-h6")

            code_input = ui.input("Code", value=item["command_code"]).props("outlined")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Update",
                    on_click=lambda: self.handle_update(
                        dialog,
                        item["id"],
                        code_input.value,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_update(
        self,
        dialog,
        item_id,
        code: str,
    ):
        await self.load_items()
        ui.notify("Command updated successfully", type="positive")
        dialog.close()

    def show_delete_dialog(self, item):
        with ui.dialog() as dialog, ui.card():
            ui.label(f"Delete {item['id']}?").classes("text-h6")
            ui.label("This action cannot be undone.")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Delete", on_click=lambda: self.handle_delete(dialog, item["id"])
                ).props("color=negative")

        dialog.open()

    def redirect_to_results(self, item):
        ui.navigate.to(f"/commands/{item['id']}/results")

    async def handle_delete(self, dialog, item_id):
        await delete_command(item_id)
        await self.load_items()
        ui.notify("Command deleted successfully", type="positive")
        dialog.close()

    async def render(self):
        """Render the CRUD page"""
        ui.label("Commands Management").classes("text-h4 q-mb-md")

        # Action buttons
        with ui.row().classes("q-mb-md"):
            ui.button(
                "Add command", icon="add", on_click=self.show_create_dialog
            ).props("color=primary")
            ui.button("Refresh", icon="refresh", on_click=self.load_items)

        @ui.refreshable
        async def table():
            await self.load_items()
            columns = [
                {"name": "id", "label": "ID", "field": "id", "align": "left"},
                {
                    "name": "order",
                    "label": "Order",
                    "field": "order",
                    "align": "left",
                },
                {
                    "name": "command_code",
                    "label": "Code",
                    "field": "command_code",
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
                    <q-btn flat dense icon="start" class="q-mr-xl"   @click="$parent.$emit('run_command', props.row)" />
                    <q-btn flat dense icon="table"   @click="$parent.$emit('show_results', props.row)" />
                </q-td>
            """,
            )

            self.table.on("edit", lambda e: self.show_edit_dialog(e.args))
            self.table.on("delete", lambda e: self.show_delete_dialog(e.args))
            self.table.on("show_results", lambda e: self.redirect_to_results(e.args))

        await table()


def init(conf: Config):
    @ui.page("/projects/{project_id}/commands")
    async def page(project_id: int):
        ui.dark_mode().auto()
        project = await get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        page = CommandsPage(conf, project)
        await page.render()
        await page.load_items()

from dataclasses import asdict

from fastapi import HTTPException
from nicegui import ui
from nicegui.elements.label import Label

from src.controllers.command_ctrl.command_ctrl import (
    add_command,
    delete_command,
    edit_command,
    list_commands,
    recreate_command,
    run_command,
    stop_command,
)
from src.controllers.ctrl_types import CommandInput
from src.controllers.manager_ctrl import Manager
from src.controllers.notification_ctrl import NotificationCtrl
from src.controllers.project_ctrl import ProjectOutput, get_project
from src.core.config import Config
from src.pages.common.nav_menu import common_nav_menu


class CommandsPage:
    def __init__(
        self,
        conf: Config,
        manager: Manager,
        notifctrl: NotificationCtrl,
        project: ProjectOutput,
    ):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.manager = manager
        self.project = project
        self.notifctrl = notifctrl
        self.running_cmd_ids = {}

    async def check_notif_and_update(self):
        notif = self.notifctrl.get_notification()
        if notif is None:
            if len(self.running_cmd_ids) > 0:
                for idx, cmd in enumerate(self.items):
                    if "is_running" in self.items[idx].keys():
                        self.items[idx]["is_running"] = False
                self.running_cmd_ids = {}
                await self.load_items()
            return

        if notif.project_id == self.project.id:
            has_changed = False
            for idx, cmd in enumerate(self.items):
                if notif.cmd_id == cmd["id"]:
                    if "is_running" not in self.items[idx].keys():
                        self.items[idx]["is_running"] = True
                        self.running_cmd_ids[notif.cmd_id] = True
                        has_changed = True
                    else:
                        if not self.items[idx]["is_running"]:
                            self.items[idx]["is_running"] = True
                            self.running_cmd_ids[notif.cmd_id] = True
                            has_changed = True
                    break

            if self.table and has_changed:
                self.table.rows = self.items  # Assign new rows
                self.table.update()

    async def load_items(self):
        cmds = await list_commands(self.project.id)
        self.items = [asdict(cmd) for cmd in cmds]
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

        errors = await add_command(self.conf, input)
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

            code_input = ui.textarea("Code", value=item["command_code"]).props(
                "outlined"
            )
            error_label = ui.label("").classes("text-red-600")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Update",
                    on_click=lambda: self.handle_update(
                        dialog,
                        item["id"],
                        code_input.value,
                        error_label,
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_update(
        self,
        dialog,
        item_id,
        code: str,
        error_label,
    ):
        input = CommandInput(
            project_id=self.project.id,
            code=code,
        )

        errors = await edit_command(self.conf, item_id, input)
        if errors is not None:
            ui.notify("Command didn't update", type="negative")
            error_label.set_text(str(errors))
            return

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

    def redirect_to_jobs(self, cmd):
        ui.navigate.to(f"/commands/{cmd['id']}/jobs")

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
                    "name": "finished_jobs",
                    "label": "Finished jobs",
                    "field": "finished_jobs",
                    "align": "left",
                },
                {
                    "name": "total_jobs",
                    "label": "Total jobs",
                    "field": "total_jobs",
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
                    <q-btn v-if="!props.row['is_running']" flat dense icon="start" class="q-mr-xl" @click="$parent.$emit('run_command', props.row)" />
                    <q-btn v-if="props.row['is_running']" flat dense icon="stop" class="q-mr-xl" @click="$parent.$emit('stop_command', props.row)" />
                    <q-btn v-if="!props.row['is_running']" flat dense icon="autorenew" class="q-mr-xl" @click="$parent.$emit('recreate_command', props.row)" />
                    <q-btn flat dense icon="table"   @click="$parent.$emit('show_jobs', props.row)" />
                </q-td>
            """,
            )

            self.table.on("edit", lambda e: self.show_edit_dialog(e.args))
            self.table.on("delete", lambda e: self.show_delete_dialog(e.args))
            self.table.on("show_jobs", lambda e: self.redirect_to_jobs(e.args))
            self.table.on(
                "run_command", lambda e: run_command(self.manager, e.args["id"])
            )
            self.table.on("stop_command", lambda e: stop_command(e.args["id"]))
            self.table.on(
                "recreate_command",
                lambda e: recreate_command(self.conf, e.args["id"]),
            )

        ui.timer(0.1, lambda: self.check_notif_and_update())
        await table()


def init(conf: Config, manager: Manager, notifctrl: NotificationCtrl):
    @ui.page("/projects/{project_id}/commands")
    async def page(project_id: int):
        ui.dark_mode().auto()
        project = await get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        page = CommandsPage(conf, manager, notifctrl, project)
        await common_nav_menu()
        await page.render()
        await page.load_items()

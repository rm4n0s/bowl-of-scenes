import time
from dataclasses import asdict

from fastapi import HTTPException
from nicegui import ui

from src.controllers.command_ctrl.command_ctrl import CommandOutput, get_command
from src.controllers.job_ctrl import list_jobs, reload_job, run_job
from src.controllers.manager_ctrl import Manager
from src.core.config import Config
from src.pages.common.nav_menu import common_nav_menu


class JobsPage:
    def __init__(self, conf: Config, manager: Manager, command: CommandOutput):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.manager = manager
        self.command = command

    async def load_items(self):
        cmds = await list_jobs(self.command.id)
        cmds_dicts = [asdict(cmd) for cmd in cmds]
        self.items = cmds_dicts
        if self.table:
            self.table.rows = self.items  # Assign new rows
            self.table.update()

    async def render(self):
        """Render the CRUD page"""
        ui.label("Jobs Management").classes("text-h4 q-mb-md")
        # Create a dialog for the image preview
        with ui.dialog() as image_dialog:
            preview_image = (
                ui.image()
                .classes("shadow-lg rounded")
                .style("max-width: 500px; max-height: 500px;")
            )

        def show_image(e):
            nonlocal preview_image
            """Show the clicked image in a dialog"""
            image_url = e.args["show_result_img"]
            preview_image.set_source(f"{image_url}?t={time.time()}")
            image_dialog.open()

        @ui.refreshable
        async def table():
            await self.load_items()
            columns = [
                {"name": "id", "label": "ID", "field": "id", "align": "left"},
                {
                    "name": "status",
                    "label": "Status",
                    "field": "status",
                    "align": "left",
                },
                {
                    "name": "show_result_img",
                    "label": "Result Image",
                    "field": "show_result_img",
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
                "body-cell-show_result_img",
                """
                <q-td :props="props">
                                <img
                                    v-if="props.row.status === 'finished'"
                                    :src="props.value"
                                    style="width: 50px; height: 50px; object-fit: cover; cursor: pointer;"
                                    @click="$parent.$emit('show_image', props.row)"
                                >
                            </q-td>
                        """,
            )
            # Add action buttons to each row
            self.table.add_slot(
                "body-cell-actions",
                """
                <q-td :props="props">
                    <q-btn flat dense icon="start" class="q-mr-xl"   @click="$parent.$emit('run_job', props.row)" />
                    <q-btn flat dense icon="autorenew" class="q-mr-xl"   @click="$parent.$emit('reload_job', props.row)" />
                </q-td>
            """,
            )
            self.table.on("show_image", show_image)
            self.table.on("run_job", lambda e: run_job(self.manager, e.args["id"]))
            self.table.on(
                "reload_job", lambda e: reload_job(self.manager, e.args["id"])
            )

        await table()


def init(conf: Config, manager: Manager | None):
    @ui.page("/commands/{command_id}/jobs")
    async def page(command_id: int):
        ui.dark_mode().auto()
        project = await get_command(command_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Command not found")

        assert manager is not None
        page = JobsPage(conf, manager, project)
        await common_nav_menu()
        await page.render()
        await page.load_items()

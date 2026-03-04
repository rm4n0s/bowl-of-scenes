import time
from dataclasses import asdict

from fastapi import HTTPException
from nicegui import ui

from src.controllers.command_ctrl.command_ctrl import CommandOutput, get_command
from src.controllers.ctrl_types import Notification
from src.controllers.job_ctrl import list_jobs, reload_job, run_job, stop_job
from src.controllers.manager_ctrl import Manager
from src.controllers.notification_ctrl import NotificationCtrl
from src.core.config import Config
from src.pages.common.nav_menu import common_nav_menu


class JobsPage:
    _prev_notif_job_id: int | None

    def __init__(
        self,
        conf: Config,
        manager: Manager,
        command: CommandOutput,
        notifctrl: NotificationCtrl,
    ):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.manager = manager
        self.command = command
        self.notifctrl = notifctrl
        self._prev_notif_job_id = None

    async def load_items(self):
        jobs = await list_jobs(self.command.id)
        self.items = [asdict(job) for job in jobs]
        if self.table:
            self.table.rows = self.items  # Assign new rows
            self.table.update()
            print("updated notif")

    async def check_notif_and_update(self):
        notif = self.notifctrl.get_notification()
        if notif is None:
            if self._prev_notif_job_id is not None:
                await self.load_items()
                self._prev_notif_job_id = None
            return

        if (
            self._prev_notif_job_id is not None
            and self._prev_notif_job_id == notif.job_id
        ):
            return

        if len(self.items) > 1:
            first_id = self.items[0]["id"]
            last_id = self.items[len(self.items) - 1]["id"]
            if first_id <= notif.job_id and last_id >= notif.job_id:
                await self.load_items()
                self._prev_notif_job_id = notif.job_id

        elif len(self.items) == 1:
            if self.items[0]["id"] == notif.job_id:
                await self.load_items()
                self._prev_notif_job_id = notif.job_id

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
                    <q-btn flat dense icon="stop" class="q-mr-xl"   @click="$parent.$emit('stop_job', props.row)" />
                    <q-btn flat dense icon="autorenew" class="q-mr-xl"   @click="$parent.$emit('reload_job', props.row)" />
                </q-td>
            """,
            )
            self.table.on("show_image", show_image)
            self.table.on("run_job", lambda e: run_job(self.manager, e.args["id"]))
            self.table.on("stop_job", lambda e: stop_job(self.manager, e.args["id"]))
            self.table.on(
                "reload_job", lambda e: reload_job(self.manager, e.args["id"])
            )

        ui.timer(0.1, lambda: self.check_notif_and_update())
        await table()


def init(conf: Config, manager: Manager | None, notifctrl: NotificationCtrl):
    @ui.page("/commands/{command_id}/jobs")
    async def page(command_id: int):
        ui.dark_mode().auto()
        project = await get_command(command_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Command not found")

        assert manager is not None
        page = JobsPage(conf, manager, project, notifctrl)
        await common_nav_menu()
        await page.render()
        await page.load_items()

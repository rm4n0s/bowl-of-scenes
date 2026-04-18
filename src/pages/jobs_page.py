import time
from dataclasses import asdict
from turtle import pos

from fastapi import HTTPException
from nicegui import ui

from src.controllers.command_ctrl.command_ctrl import get_command
from src.controllers.ctrl_types import (
    CommandOutput,
    GeneratorOutputType,
    ImageAttributes,
    JobInput,
    JobStatus,
)
from src.controllers.job_ctrl import (
    edit_job,
    list_jobs_paginated,
    run_job,
    stop_job,
)
from src.controllers.manager_ctrl import Manager
from src.controllers.notification_ctrl import NotificationCtrl
from src.core.config import Config
from src.core.utils.paginator import Paginator
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
        self._cache_notif = None

        self.paginator = Paginator(
            fetch_fn=lambda page, page_size: list_jobs_paginated(
                self.command.id, page=page, page_size=page_size
            ),
            on_change=self._update_table,
        )

    async def _update_table(self, items: list):
        rows = [asdict(job) for job in items]
        for idx, v in enumerate(rows):
            if not v.get("is_running"):
                rows[idx]["is_running"] = (
                    rows[idx]["status"] == JobStatus.PROCESSING.value
                    or rows[idx]["status"] == JobStatus.QUEUED.value
                )

        if self.table:
            self.table.rows = rows
            self.table.update()

    async def load_items(self):
        await self.paginator.load()

    async def check_notif_and_update(self):
        notif = self.notifctrl.get_notification()
        if notif is None:
            return

        if self._cache_notif is None or self._cache_notif != notif:
            self._cache_notif = notif
        else:
            return
        print(notif)
        await self.paginator.load()

    async def show_edit_dialog(self, item):
        print(item)
        with ui.dialog() as dialog, ui.card():
            ui.label("Edit Job").classes("text-h6")

            positive_input = ui.textarea(
                "Positive", value=item["prompt_positive"]
            ).props("outlined")
            negative_input = ui.textarea(
                "Negative", value=item["prompt_negative"]
            ).props("outlined")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button(
                    "Update",
                    on_click=lambda: self.handle_update(
                        dialog, item["id"], positive_input.value, negative_input.value
                    ),
                ).props("color=primary")

        dialog.open()

    async def handle_update(
        self,
        dialog,
        item_id,
        positive: str,
        negative: str,
    ):
        input = JobInput(positive=positive, negative=negative)

        await edit_job(item_id, input)
        await self.load_items()
        ui.notify("Job updated successfully", type="positive")
        dialog.close()

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
            if e.args["generator_output_type"] != GeneratorOutputType.IMAGE.value:
                return

            image_url = e.args["show_result_img"]
            attrs = ImageAttributes(**e.args["generator_output_attributes"])
            preview_image.set_source(f"{image_url}?t={time.time()}")
            preview_image.style(
                f"max-width: {attrs.width}px; max-height: {attrs.height}px;"
            )
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
                    <q-btn v-if="!props.row['is_running']" flat dense icon="start" class="q-mr-xl" @click="$parent.$emit('run_job', props.row)" />
                    <q-btn v-if="props.row['is_running']" flat dense icon="stop" class="q-mr-xl" @click="$parent.$emit('stop_job', props.row)" />
                    <q-btn v-if="!props.row['is_running']" flat dense icon="edit" class="q-mr-xl"   @click="$parent.$emit('edit_job', props.row)" />
                </q-td>
            """,
            )
            self.table.on("show_image", show_image)
            self.table.on("edit_job", lambda e: self.show_edit_dialog(e.args))
            self.table.on("run_job", lambda e: run_job(self.manager, e.args["id"]))
            self.table.on("stop_job", lambda e: stop_job(self.manager, e.args["id"]))

        self.paginator.render_controls()

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

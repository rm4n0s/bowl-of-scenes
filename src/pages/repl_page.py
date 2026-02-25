import json
import time
from datetime import datetime

from nicegui import ui
from nicegui.elements.upload_files import FileUpload
from nicegui.events import MultiUploadEventArguments

from src.controllers.ctrl_types import ReplInput
from src.controllers.manager_ctrl import Manager
from src.controllers.notification_ctrl import NotificationCtrl
from src.controllers.repl_ctrl import (
    clear_repl_job,
    run_repl,
)
from src.core.config import Config
from src.core.utils import utils
from src.pages.common.nav_menu import common_nav_menu


class ReplPage:
    main_img: ui.image
    _prev_notif_date: datetime | None

    def __init__(self, conf: Config, manager: Manager, notifctrl: NotificationCtrl):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.manager = manager
        self.notifctrl = notifctrl
        self._prev_notif_date = None

    async def handle_run(
        self,
        server_code_name: str,
        generator_code_name: str,
        group_item_code_names: str,
        prompt_positive: str,
        prompt_negative: str,
        lora_list: str,
        ipadapter_reference_image: FileUpload | None,
    ):
        lora_list_dict = utils.parse_lora_tags(prompt_positive)
        if len(lora_list_dict) > 0:
            prompt_positive = utils.remove_lora_tags(prompt_positive)
            if lora_list == "":
                lora_list = json.dumps(lora_list_dict)
            else:
                lora_list_dict_input = json.loads(lora_list)
                lora_list_dict.extend(lora_list_dict_input)
                lora_list = json.dumps(lora_list_dict)

        input = ReplInput(
            generator_code_name=generator_code_name,
            server_code_name=server_code_name,
            prompt_positive=prompt_positive,
            prompt_negative=prompt_negative,
            group_item_code_names=group_item_code_names,
            reference_ipadapter_img=ipadapter_reference_image,
            lora_list=lora_list,
        )
        await run_repl(self.conf, self.manager, input)

    def refresh_image(self):
        if self.main_img is not None:
            self.main_img.set_source(f"/result_path/repl.png?t={time.time()}")

    async def check_notif_and_update(self):
        notif = self.notifctrl.get_notification()
        if notif is None:
            if self._prev_notif_date is not None:
                self.refresh_image()
                self._prev_notif_date = None

            return

        if notif.project_id == -1:
            if self._prev_notif_date is not None:
                if self._prev_notif_date != notif.created_at:
                    self.refresh_image()
                    self._prev_notif_date = notif.created_at
            else:
                self.refresh_image()
                self._prev_notif_date = notif.created_at

    async def form(self):
        job_dict = {
            "server": "",
            "generator": "",
            "items": "",
            "positive": "",
            "negative": "",
            "lora_list": "",
        }

        server_input = ui.input("Server", value=job_dict["server"]).props("outlined")
        generator_input = ui.input("Generator", value=job_dict["generator"]).props(
            "outlined"
        )
        items_input = (
            ui.input(
                "Items",
                value=job_dict["items"],
                placeholder="group1(item2), group2(item3) ...",
            )
            .classes("w-96")
            .props("outlined")
        )
        positive_prompt_input = (
            ui.textarea("Positive prompt", value=job_dict["positive"])
            .classes("w-96")
            .props("outlined")
        )
        negative_prompt_input = (
            ui.textarea("Negative prompt", value=job_dict["negative"])
            .classes("w-96")
            .props("outlined")
        )
        lora_list_input = (
            ui.textarea(
                "LoRA in JSON",
                value=job_dict["lora_list"],
                placeholder="""
[{
"name": "style_lora.safetensors",
"strength_model": 0.7,
"strength_clip": 0.7
},{
"name": "character_lora.safetensors",
"strength_model": 0.7,
"strength_clip": 0.7
}]
            """,
            )
            .classes("w-96")
            .props("outlined")
        )
        ipadapter_reference_image_input = None

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

        async def handle_clear():
            nonlocal server_input
            nonlocal generator_input
            nonlocal items_input
            nonlocal positive_prompt_input
            nonlocal negative_prompt_input
            nonlocal lora_list_input
            nonlocal ipadapter_reference_image_input
            server_input.value = ""
            generator_input.value = ""
            items_input.value = ""
            positive_prompt_input.value = ""
            negative_prompt_input.value = ""
            lora_list_input.value = ""
            ipadapter_reference_image_input = None
            await clear_repl_job()
            self.main_img.set_source(f"/result_path/repl.png?t={time.time()}")

        ui.button(
            "Run",
            on_click=lambda: self.handle_run(
                server_input.value,
                generator_input.value,
                items_input.value,
                positive_prompt_input.value,
                negative_prompt_input.value,
                lora_list_input.value,
                ipadapter_reference_image_input,
            ),
        )
        ui.button("Clean", on_click=lambda: handle_clear())

    async def render(self):
        """Render REPL"""
        ui.label("REPL").classes("text-h4 q-mb-md")
        await clear_repl_job()
        with ui.row().style("width: 100vw; height: 100vh; margin: 0;"):
            # Left half - Form
            with ui.column().style(
                "width: 30%; height: 100%; padding: 2rem;  overflow-y: auto;"
            ):
                await self.form()

            with ui.column().style(
                "width: 50%; height: 100%; padding: 2rem; display: flex; align-items: center; justify-content: center;"
            ):
                ui.label("Preview Image").classes("text-2xl font-bold mb-4")
                self.main_img = ui.image(
                    f"/result_path/repl.png?t={time.time()}"
                ).classes("rounded-lg shadow-lg max-w-full max-h-full object-contain")

                ui.button("Refresh Image", on_click=self.refresh_image).style("""
                            position: absolute;
                            top: 20px;
                            right: 20px;
                            z-index: 10;
                        """)

            ui.timer(0.1, lambda: self.check_notif_and_update())


def init(conf: Config, manager: Manager | None, notifctrl: NotificationCtrl):
    @ui.page("/repl")
    async def page():
        ui.dark_mode().auto()
        assert manager is not None
        page = ReplPage(conf, manager, notifctrl)
        await common_nav_menu()
        await page.render()

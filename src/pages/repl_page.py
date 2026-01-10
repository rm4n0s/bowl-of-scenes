import json
import time

from nicegui import ui
from nicegui.elements.upload_files import FileUpload
from nicegui.events import MultiUploadEventArguments

from src.controllers.ctrl_types import ReplInput
from src.controllers.manager_ctrl import Manager
from src.controllers.repl_ctrl import (
    clear_repl_job,
    get_previous_job_from_repl,
    run_repl,
)
from src.core.config import Config
from src.pages.common.nav_menu import common_nav_menu


class ReplPage:
    main_img: ui.image

    def __init__(self, conf: Config, manager: Manager):
        self.items = []
        self.selected_item = None
        self.table = None
        self.conf = conf
        self.manager = manager

    async def handle_run(
        self,
        server_code_name: str,
        generator_code_name: str,
        group_item_code_names: str,
        prompt_positive: str,
        prompt_negative: str,
        lora_list: str,
        controlnet_reference_image: FileUpload | None,
        ipadapter_reference_image: FileUpload | None,
    ):
        input = ReplInput(
            generator_code_name=generator_code_name,
            server_code_name=server_code_name,
            prompt_positive=prompt_positive,
            prompt_negative=prompt_negative,
            group_item_code_names=group_item_code_names,
            reference_controlnet_img=controlnet_reference_image,
            reference_ipadapter_img=ipadapter_reference_image,
            lora_list=lora_list,
        )
        await run_repl(self.conf, self.manager, input)

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

        controlnet_reference_image_input = None

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

        async def handle_clear():
            nonlocal server_input
            nonlocal generator_input
            nonlocal items_input
            nonlocal positive_prompt_input
            nonlocal negative_prompt_input
            nonlocal lora_list_input
            nonlocal controlnet_reference_image_input
            nonlocal ipadapter_reference_image_input
            server_input.value = ""
            generator_input.value = ""
            items_input.value = ""
            positive_prompt_input.value = ""
            negative_prompt_input.value = ""
            lora_list_input.value = ""
            controlnet_reference_image_input = None
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
                controlnet_reference_image_input,
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

                def refresh_image():
                    self.main_img.set_source(f"/result_path/repl.png?t={time.time()}")

                ui.button("Refresh Image", on_click=refresh_image).style("""
                            position: absolute;
                            top: 20px;
                            right: 20px;
                            z-index: 10;
                        """)


def init(conf: Config, manager: Manager | None):
    @ui.page("/repl")
    async def page():
        ui.dark_mode().auto()
        assert manager is not None
        page = ReplPage(conf, manager)
        await common_nav_menu()
        await page.render()

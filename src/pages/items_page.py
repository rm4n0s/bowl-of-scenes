import json
from dataclasses import asdict, dataclass

from fastapi import HTTPException
from nicegui import ui
from nicegui.elements.textarea import Textarea
from nicegui.elements.upload_files import FileUpload
from nicegui.events import MultiUploadEventArguments

from src.controllers.ctrl_types import (
    ControlNetConfigInput,
    ControlNetType,
    ItemIPAdapterInput,
    ItemIPAdapterOutput,
)
from src.controllers.group_ctrl import GroupOutput, get_group
from src.controllers.item_ctrl import (
    ItemInput,
    add_item,
    delete_item,
    edit_item,
    list_items,
)
from src.core.config import Config
from src.core.utils import utils
from src.pages.common.nav_menu import common_nav_menu


@dataclass
class IPAdapterForm:
    ipadapter_clip_vision_model_input: ui.input
    ipadapter_model_input: ui.input
    ipadapter_weight_input: ui.number
    ipadapter_weight_type_input: ui.input
    ipadapter_start_at_input: ui.number
    ipadapter_end_at_input: ui.number
    ipadapter_reference_image_input: FileUpload | None


class ItemsPage:
    table: ui.table | None
    input_controlnets: list[ControlNetConfigInput]

    def __init__(self, conf: Config, group: GroupOutput):
        self.items = []
        self.input_controlnets = []
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

    async def add_controlnet(
        self,
        type_of_controlnet: ControlNetType,
        image_path: FileUpload | None,
        is_reference: bool,
        model_pattern: str,
        strength: float,
    ):
        assert image_path
        self.input_controlnets.append(
            ControlNetConfigInput(
                type_of_controlnet=type_of_controlnet,
                image_path=image_path,
                is_reference=is_reference,
                model_pattern=model_pattern,
                strength=strength,
            )
        )

    async def show_controllnet_dialog(self):
        with ui.dialog() as add_dialog, ui.card().classes("w-80"):
            ui.label("Add Controlnet").classes("text-lg font-bold mb-4")

            controlnet_type_select = ui.select(
                label="Controlnet type",
                options=[p.value for p in ControlNetType],
                value=ControlNetType.OPENPOSE.value,
            )

            controlnet_image_input = None

            async def handle_controlnet_upload(event: MultiUploadEventArguments):
                nonlocal controlnet_image_input
                if event.files:
                    controlnet_image_input = event.files[0]

            ui.label("Upload image").classes("text-h6")
            ui.upload(
                on_multi_upload=lambda e: handle_controlnet_upload(e),
                auto_upload=True,
                max_files=1,
            ).props('accept="image/jpeg,image/png"')

            is_reference_input = ui.checkbox("Is Reference", value=False)
            model_pattern_input = ui.input(
                "Model pattern", placeholder="example_openpose.safetensors"
            ).classes("w-full")
            strength_input = ui.number("Strength", value=2.5)
            with ui.row().classes("w-full gap-2 mt-4"):
                ui.button("Cancel", on_click=add_dialog.close).classes("flex-1")
                ui.button(
                    "Add",
                    on_click=lambda: self.add_controlnet(
                        controlnet_type_select.value,  # pyright: ignore[reportArgumentType]
                        controlnet_image_input,
                        is_reference_input.value,
                        model_pattern_input.value,
                        strength_input.value,
                    ),
                    icon="check",
                ).classes("flex-1")

        add_dialog.open()

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
[{
   "name": "style_lora",
   "strength_model": 0.7,
   "strength_clip": 0.7
}]
                    """,
                ).props("outlined")

            coordinated_regions_input = None
            if self.group.use_coordinates_region:
                coordinated_regions_input = ui.textarea(
                    "Coordinated Regions in JSON",
                    placeholder="""
            [{
               "keyword": "left",
               "width": 512,
               "height": 1024,
               "x": 0,
               "y": 0
            }]
                                """,
                ).props("outlined")

            ipadapter_form = None
            if self.group.use_ip_adapter:
                ipadapter_model_input = ui.input("IPAdapter's Model Name").props(
                    "outlined"
                )
                ipadapter_clip_vision_model_input = ui.input(
                    "IPAdapter's Clip Vision Model Name"
                ).props("outlined")
                ipadapter_weight_input = ui.number(
                    "IPAdapter Start At", value=0.8, format="%.2f"
                ).props("outlined")
                ipadapter_weight_type_input = ui.input(
                    "IPAdapter Weight Type", value="linear"
                ).props("outlined")
                ipadapter_start_at_input = ui.number(
                    "IPAdapter Start At", value=0.0, format="%.2f"
                ).props("outlined")
                ipadapter_end_at_input = ui.number(
                    "IPAdapter End At", value=1.0, format="%.2f"
                ).props("outlined")

                ipadapter_form = IPAdapterForm(
                    ipadapter_model_input=ipadapter_model_input,
                    ipadapter_clip_vision_model_input=ipadapter_clip_vision_model_input,
                    ipadapter_weight_input=ipadapter_weight_input,
                    ipadapter_weight_type_input=ipadapter_weight_type_input,
                    ipadapter_start_at_input=ipadapter_start_at_input,
                    ipadapter_end_at_input=ipadapter_end_at_input,
                    ipadapter_reference_image_input=None,
                )

                async def handle_ipadapter_upload(event: MultiUploadEventArguments):
                    nonlocal ipadapter_form
                    if event.files:
                        assert ipadapter_form is not None
                        ipadapter_form.ipadapter_reference_image_input = event.files[0]

                ui.label("Upload IP Adapter image").classes("text-h6")
                ui.upload(
                    on_multi_upload=lambda e: handle_ipadapter_upload(e),
                    auto_upload=True,
                    max_files=1,
                ).props('accept="image/jpeg,image/png"')

            mask_region_reference_image_input = None
            if self.group.use_mask_region:

                async def handle_mask_region_reference_image_upload(
                    event: MultiUploadEventArguments,
                ):
                    nonlocal mask_region_reference_image_input
                    if event.files:
                        mask_region_reference_image_input = event.files[0]

                ui.label("Upload Mask Region Reference image").classes("text-h6")
                ui.upload(
                    on_multi_upload=lambda e: handle_mask_region_reference_image_upload(
                        e
                    ),
                    auto_upload=True,
                    max_files=1,
                ).props('accept="image/jpeg,image/png"')

            controlnets_input: list[ControlNetConfigInput] = []
            if self.group.use_controlnet:
                ui.label("My Controlnets").classes("text-xl font-bold mb-4")

                # Container for task list
                controlnets_container = ui.column().classes("w-full mb-4")

                # Add task button
                ui.button(
                    "Add Controlnet", on_click=self.show_controllnet_dialog, icon="add"
                ).classes("w-full")

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
                        coordinated_regions_input,
                        ipadapter_form,
                        mask_region_reference_image_input,
                        controlnets_input,
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
        coordinated_regions_input: Textarea | None,
        ipadapter_form: IPAdapterForm | None,
        mask_region_reference_image: FileUpload | None,
        controlnets_input: list[ControlNetConfigInput],
        thumbnail_image: FileUpload | None,
    ):
        lora = None
        if self.group.use_lora:
            if lora_input is not None:
                if len(lora_input.value) > 0:
                    lora = lora_input.value

            lora_list_dict = utils.parse_lora_tags(positive_prompt)
            if len(lora_list_dict) > 0:
                positive_prompt = utils.remove_lora_tags(positive_prompt)
                if lora is None:
                    lora = json.dumps(lora_list_dict)
                else:
                    lora_list_dict_input = json.loads(lora)
                    lora_list_dict.extend(lora_list_dict_input)
                    lora = json.dumps(lora_list_dict)

        coordinated_regions = None
        if coordinated_regions_input is not None:
            if len(coordinated_regions_input.value) > 0:
                coordinated_regions = coordinated_regions_input.value

        item_ipadapter_input = None
        if (
            ipadapter_form is not None
            and ipadapter_form.ipadapter_reference_image_input is not None
        ):
            item_ipadapter_input = ItemIPAdapterInput(
                reference_image=ipadapter_form.ipadapter_reference_image_input,
                weight=ipadapter_form.ipadapter_weight_input.value,
                weight_type=ipadapter_form.ipadapter_weight_type_input.value,
                model_name=ipadapter_form.ipadapter_model_input.value,
                clip_vision_model=ipadapter_form.ipadapter_clip_vision_model_input.value,
                start_at=ipadapter_form.ipadapter_start_at_input.value,
                end_at=ipadapter_form.ipadapter_end_at_input.value,
            )

        input = ItemInput(
            group_id=self.group.id,
            name=name,
            code_name=code_name,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            lora=lora,
            coordinated_regions=coordinated_regions,
            ipadapter=item_ipadapter_input,
            controlnets=controlnets_input,
            mask_region_reference_image=mask_region_reference_image,
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

            coordinated_regions_input = None
            if self.group.use_coordinates_region:
                cr = ""
                if item["coordinated_regions"] is not None:
                    cr = item["coordinated_regions"]

                coordinated_regions_input = ui.textarea(
                    "Coordinated Regions in JSON",
                    value=cr,
                ).props("outlined")

            ipadapter_form = None
            if self.group.use_ip_adapter:
                ipadapter_prv = ItemIPAdapterOutput(
                    reference_image="",
                    show_reference_image="",
                    weight=0.8,
                    weight_type="original",
                    start_at=0.0,
                    end_at=1.0,
                    clip_vision_model="",
                    model_name="",
                )
                if item["ipadapter"] is not None:
                    ipadapter_prv = ItemIPAdapterOutput(**item["ipadapter"])

                ipadapter_model_input = ui.input(
                    "IPAdapter's Model Name", value=ipadapter_prv.model_name
                ).props("outlined")
                ipadapter_clip_vision_model_input = ui.input(
                    "IPAdapter's Clip Vision Model Name",
                    value=ipadapter_prv.clip_vision_model,
                ).props("outlined")
                ipadapter_weight_input = ui.number(
                    "IPAdapter Start At", value=ipadapter_prv.weight, format="%.2f"
                ).props("outlined")
                ipadapter_weight_type_input = ui.input(
                    "IPAdapter Weight Type", value=ipadapter_prv.weight_type
                ).props("outlined")
                ipadapter_start_at_input = ui.number(
                    "IPAdapter Start At", value=ipadapter_prv.start_at, format="%.2f"
                ).props("outlined")
                ipadapter_end_at_input = ui.number(
                    "IPAdapter End At", value=ipadapter_prv.end_at, format="%.2f"
                ).props("outlined")

                ipadapter_form = IPAdapterForm(
                    ipadapter_model_input=ipadapter_model_input,
                    ipadapter_clip_vision_model_input=ipadapter_clip_vision_model_input,
                    ipadapter_weight_input=ipadapter_weight_input,
                    ipadapter_weight_type_input=ipadapter_weight_type_input,
                    ipadapter_start_at_input=ipadapter_start_at_input,
                    ipadapter_end_at_input=ipadapter_end_at_input,
                    ipadapter_reference_image_input=None,
                )

                async def handle_ipadapter_upload(event: MultiUploadEventArguments):
                    nonlocal ipadapter_form
                    if event.files:
                        assert ipadapter_form is not None
                        ipadapter_form.ipadapter_reference_image_input = event.files[0]

                ui.label("Upload IP Adapter image").classes("text-h6")
                ui.upload(
                    on_multi_upload=lambda e: handle_ipadapter_upload(e),
                    auto_upload=True,
                    max_files=1,
                ).props('accept="image/jpeg,image/png"')

            mask_region_reference_image_input = None
            if self.group.use_mask_region:

                async def handle_mask_region_reference_image_upload(
                    event: MultiUploadEventArguments,
                ):
                    nonlocal mask_region_reference_image_input
                    if event.files:
                        mask_region_reference_image_input = event.files[0]

                ui.label("Upload Color code image").classes("text-h6")
                ui.upload(
                    on_multi_upload=lambda e: handle_mask_region_reference_image_upload(
                        e
                    ),
                    auto_upload=True,
                    max_files=1,
                ).props('accept="image/jpeg,image/png"')

            thumbnail_image_input = None

            async def handle_thumbnail_upload(event: MultiUploadEventArguments):
                nonlocal thumbnail_image_input
                if event.files:
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
                        coordinated_regions_input,
                        ipadapter_form,
                        mask_region_reference_image_input,
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
        coordinated_regions_input: Textarea | None,
        ipadapter_form: IPAdapterForm | None,
        color_coded_reference_image: FileUpload | None,
        thumbnail_image: FileUpload | None,
    ):
        lora = None
        if self.group.use_lora:
            if lora_input is not None:
                if len(lora_input.value) > 0:
                    lora = lora_input.value

            lora_list_dict = utils.parse_lora_tags(positive_prompt)
            if len(lora_list_dict) > 0:
                positive_prompt = utils.remove_lora_tags(positive_prompt)
                if lora is None:
                    lora = json.dumps(lora_list_dict)
                else:
                    lora_list_dict_input = json.loads(lora)
                    lora_list_dict.extend(lora_list_dict_input)
                    lora = json.dumps(lora_list_dict)

        cr = None
        if coordinated_regions_input is not None:
            if len(coordinated_regions_input.value) > 0:
                cr = coordinated_regions_input.value

        item_ipadapter_input = None
        if (
            ipadapter_form is not None
            and ipadapter_form.ipadapter_reference_image_input is not None
        ):
            item_ipadapter_input = ItemIPAdapterInput(
                reference_image=ipadapter_form.ipadapter_reference_image_input,
                weight=ipadapter_form.ipadapter_weight_input.value,
                weight_type=ipadapter_form.ipadapter_weight_type_input.value,
                model_name=ipadapter_form.ipadapter_model_input.value,
                clip_vision_model=ipadapter_form.ipadapter_clip_vision_model_input.value,
                start_at=ipadapter_form.ipadapter_start_at_input.value,
                end_at=ipadapter_form.ipadapter_end_at_input.value,
            )

        input = ItemInput(
            group_id=self.group.id,
            name=name,
            code_name=code_name,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            lora=lora,
            coordinated_regions=cr,
            ipadapter=item_ipadapter_input,
            mask_region_reference_image=color_coded_reference_image,
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
                    "name": "mask_region_images_keys",
                    "label": "Mask Region keys",
                    "field": "mask_region_images_keys",
                    "align": "left",
                },
                {
                    "name": "coordinated_region_keys",
                    "label": "Coordinated Region keys",
                    "field": "coordinated_region_keys",
                    "align": "left",
                },
                {
                    "name": "show_ipadapter_reference_image",
                    "label": "IPAdapter image",
                    "field": "ipadapter.show_reference_image",
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

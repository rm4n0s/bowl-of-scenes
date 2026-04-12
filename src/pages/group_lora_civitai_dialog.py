from dataclasses import dataclass, field
from datetime import datetime

from nicegui import ui

from src.controllers.category_ctrl import list_categories
from src.controllers.ctrl_types import CivitaiLora, GroupInput
from src.controllers.group_ctrl import add_group_of_loras_civitai
from src.core.config import Config


@dataclass
class CivitaiLoraFormData:
    name: str = ""
    code_name: str = ""
    civitai_loras: list[CivitaiLora] = field(default_factory=list)


def open_add_civitai_lora_to_list_dialog(
    form_data: CivitaiLoraFormData, items_container
):
    """Opens a nested dialog to add a new model item."""
    with ui.dialog() as add_dialog, ui.card().classes("w-96 p-6 gap-4"):
        ui.label("Add Model Item").classes("text-lg font-semibold text-gray-700")
        ui.separator()

        model_id_input = ui.input(
            label="Model ID", placeholder="e.g. stable-diffusion-v1"
        ).classes("w-full")

        model_strength_input = ui.number(
            label="Model Strength",
            placeholder="0.0 – 1.0",
            min=0.0,
            max=1.0,
            step=0.01,
            format="%.2f",
        ).classes("w-full")

        model_clip_input = ui.number(
            label="Model Clip", placeholder="e.g. 1.0", step=0.01, format="%.2f"
        ).classes("w-full")

        error_label = ui.label("").classes("text-red-500 text-sm hidden")

        def confirm_add():
            # Validate
            if not model_id_input.value:
                error_label.set_text("Model ID is required.")
                error_label.classes(remove="hidden")
                return
            if model_strength_input.value is None:
                error_label.set_text("Model Strength is required.")
                error_label.classes(remove="hidden")
                return
            if model_clip_input.value is None:
                error_label.set_text("Model Clip is required.")
                error_label.classes(remove="hidden")
                return

            item = CivitaiLora(
                model_id=int(model_id_input.value),
                model_strength=float(model_strength_input.value),
                model_clip=float(model_clip_input.value),
            )
            form_data.civitai_loras.append(item)
            refresh_civitai_loras(items_container, form_data)
            add_dialog.close()

        with ui.row().classes("w-full justify-end gap-2 pt-2"):
            ui.button("Cancel", on_click=add_dialog.close).props("flat").classes(
                "text-gray-500"
            )
            ui.button("Add", on_click=confirm_add).classes("bg-blue-600 text-white")

    add_dialog.open()


def refresh_civitai_loras(container, form_data: CivitaiLoraFormData):
    """Clears and redraws the items list inside the container."""
    container.clear()
    with container:
        if not form_data.civitai_loras:
            ui.label("No items added yet.").classes("text-gray-400 text-sm italic py-2")
        for idx, item in enumerate(form_data.civitai_loras):
            with ui.card().classes("w-full p-3 bg-gray-50 border border-gray-200"):
                with ui.row().classes("w-full items-center justify-between"):
                    with ui.column().classes("gap-0"):
                        ui.label(str(item.model_id)).classes(
                            "font-medium text-gray-800"
                        )
                        ui.label(
                            f"Strength: {item.model_strength:.2f}  •  Clip: {item.model_clip:.2f}"
                        ).classes("text-sm text-gray-500")

                    def make_delete(i):
                        def delete():
                            form_data.civitai_loras.pop(i)
                            refresh_civitai_loras(container, form_data)

                        return delete

                    ui.button(icon="delete", on_click=make_delete(idx)).props(
                        "flat round dense"
                    ).classes("text-red-400 hover:text-red-600")


async def show_create_group_civitai_loras(cfg: Config, acb):
    """Opens the main form dialog."""
    form_data = CivitaiLoraFormData()
    categories = await list_categories()
    cat_dicts = {}
    for cat in categories:
        cat_dicts[cat.id] = cat.name

    with ui.dialog() as main_dialog, ui.card().classes("w-[520px] p-6 gap-4"):
        ui.label("Create New Configuration").classes(
            "text-xl font-semibold text-gray-700"
        )
        ui.separator()

        name_input = ui.input(
            label="Name", placeholder="Enter configuration name"
        ).classes("w-full")

        code_name_input = ui.input(
            label="Code Name", placeholder="e.g. my_config_v1"
        ).classes("w-full")

        comfyui_path_input = ui.input(
            label="Comfyui's folder path", placeholder="/ComfyUI"
        ).classes("w-full")

        comfyui_lora_subfolder_name = ui.input(
            label="Comfyui's lora subfolder name",
            value=datetime.now().strftime("%Y_%m_%d"),
        ).classes("w-full")

        category_id_input = ui.select(cat_dicts, value=categories[0].id)

        ui.separator()

        # Items section header
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Model Items").classes("font-medium text-gray-700")
            ui.button(
                icon="add",
                on_click=lambda: open_add_civitai_lora_to_list_dialog(
                    form_data, items_container
                ),
            ).props("round dense").classes("bg-blue-600 text-white").tooltip("Add item")

        # Items list container
        items_container = ui.column().classes("w-full gap-2")
        refresh_civitai_loras(items_container, form_data)

        ui.separator()

        error_label = ui.label("").classes("text-red-500 text-sm hidden")

        async def submit():
            if not name_input.value:
                error_label.set_text("Name is required.")
                error_label.classes(remove="hidden")
                return
            if not code_name_input.value:
                error_label.set_text("Code Name is required.")
                error_label.classes(remove="hidden")
                return

            form_data.name = name_input.value
            form_data.code_name = code_name_input.value
            group_input = GroupInput(
                name=form_data.name,
                code_name=form_data.code_name,
                category_id=int(category_id_input.value),  # pyright: ignore[reportArgumentType]
                description="",
                use_lora=True,
                use_controlnet=False,
                use_ip_adapter=False,
                use_mask_region=False,
                use_type_attributes=False,
                use_coordinates_region=False,
                thumbnail_image=None,
            )
            await add_group_of_loras_civitai(
                cfg,
                form_data.civitai_loras,
                group_input,
                comfyui_path_input.value,
                comfyui_lora_subfolder_name.value,
            )
            await acb()
            # ✅ Here you'd do something with form_data
            ui.notify(
                f"Saved '{form_data.name}' with {len(form_data.civitai_loras)} item(s).",
                type="positive",
            )
            main_dialog.close()

        with ui.row().classes("w-full justify-end gap-2 pt-2"):
            ui.button("Cancel", on_click=main_dialog.close).props("flat").classes(
                "text-gray-500"
            )
            ui.button("Save", on_click=submit).classes("bg-blue-600 text-white")

    main_dialog.open()

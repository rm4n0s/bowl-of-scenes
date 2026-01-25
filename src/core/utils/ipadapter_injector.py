import re
from typing import Any


def get_max_node_id(workflow: dict[str, Any]) -> int:
    """Extract the maximum numeric node ID from workflow keys."""
    max_id = 0
    for key in workflow.keys():
        numbers = re.findall(r"\d+", str(key))
        if numbers:
            max_id = max(max_id, max(int(n) for n in numbers))
    return max_id


def generate_unique_id(workflow: dict[str, Any], base_id: int) -> str:
    """Generate a unique node ID that doesn't exist in the workflow."""
    node_id = str(base_id)
    while node_id in workflow:
        base_id += 1
        node_id = str(base_id)
    return node_id


def add_multiple_ipadapters_to_workflow(
    workflow: dict[str, Any],
    reference_images: list[dict[str, Any]],
    clip_vision_model: str = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors",
) -> dict[str, Any]:
    """
    Add multiple IPAdapter nodes to a ComfyUI workflow in sequence.
    Works with ComfyUI_IPAdapter_plus extension.
    """
    # Find the highest node ID
    max_id = get_max_node_id(workflow)

    # Find the KSampler node
    ksampler_id = None
    model_input = None

    for node_id, node_data in workflow.items():
        class_type = node_data.get("class_type", "")
        if class_type in ["KSampler", "KSamplerAdvanced"]:
            ksampler_id = node_id
            model_input = node_data["inputs"].get("model")
            break

    if not ksampler_id:
        raise ValueError("No KSampler node found in workflow")

    # Add CLIPVisionLoader (shared by all IPAdapters)
    current_id = max_id + 1
    clip_vision_loader_id = generate_unique_id(workflow, current_id)
    workflow[clip_vision_loader_id] = {
        "inputs": {"clip_name": clip_vision_model},
        "class_type": "CLIPVisionLoader",
        "_meta": {"title": "Load CLIP Vision"},
    }

    current_id = int(clip_vision_loader_id) + 1
    current_model_input = model_input

    # Add each IPAdapter in sequence
    for idx, ref_img in enumerate(reference_images):
        path = ref_img["path"]
        model_name = ref_img.get("model", "ip-adapter_sd15.bin")
        weight = ref_img.get("weight", 1.0)
        weight_type = ref_img.get("weight_type", "linear")
        start_at = ref_img.get("start_at", 0.0)
        end_at = ref_img.get("end_at", 1.0)

        # LoadImage node
        load_image_id = generate_unique_id(workflow, current_id)
        workflow[load_image_id] = {
            "inputs": {"image": path},
            "class_type": "LoadImage",
            "_meta": {"title": f"IPAdapter Reference {idx + 1}"},
        }
        current_id = int(load_image_id) + 1

        # IPAdapterModelLoader node
        ipadapter_loader_id = generate_unique_id(workflow, current_id)
        workflow[ipadapter_loader_id] = {
            "inputs": {"ipadapter_file": model_name},
            "class_type": "IPAdapterModelLoader",
            "_meta": {"title": f"IPAdapter Model {idx + 1}"},
        }
        current_id = int(ipadapter_loader_id) + 1

        # IPAdapterAdvanced node - THIS IS THE CORRECT CLASS NAME
        ipadapter_apply_id = generate_unique_id(workflow, current_id)
        workflow[ipadapter_apply_id] = {
            "inputs": {
                "weight": weight,
                "weight_type": weight_type,
                "start_at": start_at,
                "end_at": end_at,
                "model": current_model_input,
                "ipadapter": [ipadapter_loader_id, 0],
                "image": [load_image_id, 0],
                "clip_vision": [clip_vision_loader_id, 0],
                "embeds_scaling": "V only",
                "combine_embeds": "concat",
            },
            "class_type": "IPAdapterAdvanced",
            "_meta": {"title": f"Apply IPAdapter {idx + 1}"},
        }

        current_id = int(ipadapter_apply_id) + 1

        # The output of this IPAdapter becomes the input for the next
        current_model_input = [ipadapter_apply_id, 0]

    # Update KSampler to use the final IPAdapter output
    workflow[ksampler_id]["inputs"]["model"] = current_model_input

    return workflow

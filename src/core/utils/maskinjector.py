import copy
from typing import Any

from src.db.records.job_rec import RegionPrompt


def inject_masks(
    original_workflow: dict[str, Any], prompts: list[RegionPrompt]
) -> dict[str, Any]:
    if not prompts:
        return copy.deepcopy(original_workflow)

    workflow = copy.deepcopy(original_workflow)

    # Find the maximum node ID to start assigning new IDs
    max_id = max(int(k) for k in workflow.keys() if k.isdigit())
    next_id = max_id + 1

    def get_next_id() -> str:
        nonlocal next_id
        current = next_id
        next_id += 1
        return str(current)

    # Find the KSampler node
    ksampler_id = None
    for node_id, node in workflow.items():
        if node.get("class_type") == "KSampler":
            ksampler_id = node_id
            break

    if ksampler_id is None:
        raise ValueError("No KSampler node found in the workflow")

    def find_base_conditioning(positive_link):
        current_link = positive_link
        consumer_id = ksampler_id
        consumer_key = "positive"
        while True:
            current_id, current_out = current_link
            current_node = workflow.get(current_id)
            if current_node is None:
                raise ValueError("Invalid node ID in conditioning chain")
            class_type = current_node.get("class_type")
            if class_type == "CLIPTextEncode":
                return [current_id, current_out], consumer_id, consumer_key
            elif class_type == "ControlNetApplyAdvanced":
                current_link = current_node["inputs"].get("positive")
                if not isinstance(current_link, list) or len(current_link) != 2:
                    raise ValueError(
                        "ControlNetApplyAdvanced positive input is not properly linked"
                    )
                consumer_id = current_id
                consumer_key = "positive"
            elif class_type == "ControlNetApply":
                current_link = current_node["inputs"].get("conditioning")
                if not isinstance(current_link, list) or len(current_link) != 2:
                    raise ValueError(
                        "ControlNetApply conditioning input is not properly linked"
                    )
                consumer_id = current_id
                consumer_key = "conditioning"
            else:
                raise ValueError(
                    f"Unsupported node type in conditioning chain: {class_type}"
                )

    # Get the base conditioning and the consumer
    positive_link = workflow[ksampler_id]["inputs"].get("positive")
    if not isinstance(positive_link, list) or len(positive_link) != 2:
        raise ValueError("KSampler's positive input is not properly linked")

    base_cond_link, consumer_id, consumer_key = find_base_conditioning(positive_link)
    base_cond_id, base_cond_output = base_cond_link

    # Get the base node and CLIP
    base_node = workflow.get(base_cond_id)
    if base_node is None or base_node.get("class_type") != "CLIPTextEncode":
        raise ValueError("Base conditioning node is not a CLIPTextEncode")

    clip_link = base_node["inputs"].get("clip")
    if not isinstance(clip_link, list) or len(clip_link) != 2:
        raise ValueError("Base CLIPTextEncode does not have a valid clip input")

    clip_id, clip_output = clip_link

    # Start with the base conditioning as the current conditioning
    current_cond = [base_cond_id, base_cond_output]

    for prompt_obj in prompts:
        # Validate that we have either mask_file or coordinates
        if prompt_obj.mask_file is None and prompt_obj.coordinates is None:
            raise ValueError(
                f"RegionPrompt for '{prompt_obj.keyword}' must have either mask_file or coordinates"
            )

        if prompt_obj.mask_file is not None and prompt_obj.coordinates is not None:
            raise ValueError(
                f"RegionPrompt for '{prompt_obj.keyword}' cannot have both mask_file and coordinates"
            )

        # Add CLIPTextEncode for the regional prompt
        region_encode_id = get_next_id()
        workflow[region_encode_id] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_obj.prompt, "clip": [clip_id, clip_output]},
        }

        # Branch based on whether we're using mask or coordinates
        if prompt_obj.mask_file is not None:
            # ===== MASK PATH =====
            # Add LoadImage node for the mask file
            load_mask_id = get_next_id()
            workflow[load_mask_id] = {
                "class_type": "LoadImage",
                "inputs": {"image": prompt_obj.mask_file},
            }

            # Add ImageToMask node to convert image to mask
            mask_id = get_next_id()
            workflow[mask_id] = {
                "class_type": "ImageToMask",
                "inputs": {
                    "image": [load_mask_id, 0],
                    "channel": "red",
                },
            }

            # Add ConditioningSetMask to apply the mask
            conditioned_id = get_next_id()
            workflow[conditioned_id] = {
                "class_type": "ConditioningSetMask",
                "inputs": {
                    "conditioning": [region_encode_id, 0],
                    "mask": [mask_id, 0],
                    "strength": 1.0,
                    "set_cond_area": "default",
                },
            }

        else:
            # ===== COORDINATES PATH =====
            # Add ConditioningSetArea using coordinates
            assert prompt_obj.coordinates is not None
            conditioned_id = get_next_id()
            workflow[conditioned_id] = {
                "class_type": "ConditioningSetArea",
                "inputs": {
                    "conditioning": [region_encode_id, 0],
                    "width": prompt_obj.coordinates.width,
                    "height": prompt_obj.coordinates.height,
                    "x": prompt_obj.coordinates.x,
                    "y": prompt_obj.coordinates.y,
                    "strength": 1.0,
                },
            }

        # Add ConditioningCombine to combine with the current conditioning
        combine_id = get_next_id()
        workflow[combine_id] = {
            "class_type": "ConditioningCombine",
            "inputs": {
                "conditioning_1": current_cond,
                "conditioning_2": [conditioned_id, 0],
            },
        }

        # Update current conditioning to the new combine
        current_cond = [combine_id, 0]

    # Update the consumer's input to the final combined conditioning
    workflow[consumer_id]["inputs"][consumer_key] = current_cond

    return workflow

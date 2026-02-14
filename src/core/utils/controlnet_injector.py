from typing import Any

from src.controllers.ctrl_types import (
    CONTROLNET_PREPROCESSORS,
    ControlNetConfig,
    ControlNetType,
)


def inject_controlnet(
    workflow: dict[str, Any],
    controlnet_configs: list[ControlNetConfig],
    save_preprocessed: bool = True,
) -> dict[str, Any]:
    """
    Injects ControlNet nodes into a ComfyUI workflow.

    Args:
        workflow: Original ComfyUI workflow in API format (dict of nodes)
        controlnet_configs: List of ControlNet configurations to inject
        save_preprocessed: If True, saves preprocessed images to output folder for verification

    Returns:
        Modified workflow dict with injected ControlNet nodes
    """
    if not controlnet_configs:
        return workflow

    # Find the highest numeric node ID to start adding new nodes
    numeric_ids = []
    for node_id in workflow.keys():
        try:
            numeric_ids.append(int(node_id))
        except ValueError:
            pass

    if numeric_ids:
        max_node_id = max(numeric_ids)
    else:
        max_node_id = 1000

    current_id = max_node_id + 1

    # Find KSampler node and get its conditioning inputs
    ksampler_id = None
    positive_source = None
    negative_source = None

    for node_id, node in workflow.items():
        if node.get("class_type") in ["KSampler", "KSamplerAdvanced"]:
            ksampler_id = node_id
            positive_source = node["inputs"]["positive"]
            negative_source = node["inputs"]["negative"]
            break

    if not ksampler_id:
        raise ValueError("No KSampler node found in workflow")

    # Track the current conditioning outputs (for chaining multiple controlnets)
    current_positive = positive_source
    current_negative = negative_source

    # Inject each ControlNet
    for idx, config in enumerate(controlnet_configs):
        preprocessor_class = CONTROLNET_PREPROCESSORS.get(config.type_of_controlnet)

        # DEBUG: Print what we found
        print(f"[DEBUG] ControlNet {idx}:")
        print(f"  - Type: {config.type_of_controlnet}")
        print(f"  - Type value: {config.type_of_controlnet.value}")
        print(f"  - is_reference: {config.is_reference}")
        print(f"  - Preprocessor class: {preprocessor_class}")

        # 1. LoadImage node
        load_image_id = str(current_id)
        workflow[load_image_id] = {
            "inputs": {"image": config.image_path, "upload": "image"},
            "class_type": "LoadImage",
            "_meta": {
                "title": f"Load ControlNet Image ({config.type_of_controlnet.value})"
            },
        }
        current_id += 1

        # 2. Preprocessor node (if is_reference is True and preprocessor exists)
        if config.is_reference and preprocessor_class:
            print(f"  - Creating preprocessor node!")
            preprocessor_id = str(current_id)
            preprocessor_inputs: dict[str, Any] = {"image": [load_image_id, 0]}

            # Add default parameters based on preprocessor type
            if config.type_of_controlnet == ControlNetType.CANNY:
                preprocessor_inputs.update(
                    {"low_threshold": 100, "high_threshold": 200}
                )
            elif config.type_of_controlnet in [
                ControlNetType.OPENPOSE,
                ControlNetType.DWPOSE,
            ]:
                preprocessor_inputs.update(
                    {
                        "detect_hand": "enable",
                        "detect_body": "enable",
                        "detect_face": "enable",
                    }
                )
            elif config.type_of_controlnet == ControlNetType.MIDAS:
                preprocessor_inputs.update({"a": 6.2, "bg_threshold": 0.1})

            workflow[preprocessor_id] = {
                "inputs": preprocessor_inputs,
                "class_type": preprocessor_class,
                "_meta": {"title": f"{config.type_of_controlnet.value} Preprocessor"},
            }
            current_id += 1
            control_image_source = [preprocessor_id, 0]

            # 2a. SaveImage node to save the preprocessed output for verification
            if save_preprocessed:
                print(f"  - Creating SaveImage node!")
                save_preprocessed_id = str(current_id)
                workflow[save_preprocessed_id] = {
                    "inputs": {
                        "images": [preprocessor_id, 0],
                        "filename_prefix": f"preprocessed_{config.type_of_controlnet.value}_{idx}",
                    },
                    "class_type": "SaveImage",
                    "_meta": {
                        "title": f"Save Preprocessed {config.type_of_controlnet.value}"
                    },
                }
                current_id += 1
        else:
            print(
                f"  - Skipping preprocessor (is_reference={config.is_reference}, preprocessor_class={preprocessor_class})"
            )
            # Use image directly without preprocessing
            control_image_source = [load_image_id, 0]

        # 3. ControlNetLoader node
        controlnet_loader_id = str(current_id)
        workflow[controlnet_loader_id] = {
            "inputs": {"control_net_name": config.model_pattern},
            "class_type": "ControlNetLoader",
            "_meta": {"title": f"Load ControlNet ({config.type_of_controlnet.value})"},
        }
        current_id += 1

        # 4. ControlNetApplyAdvanced node
        controlnet_apply_id = str(current_id)
        workflow[controlnet_apply_id] = {
            "inputs": {
                "strength": config.strength,
                "start_percent": 0.0,
                "end_percent": 1.0,
                "positive": current_positive,
                "negative": current_negative,
                "control_net": [controlnet_loader_id, 0],
                "image": control_image_source,
            },
            "class_type": "ControlNetApplyAdvanced",
            "_meta": {"title": f"Apply ControlNet ({config.type_of_controlnet.value})"},
        }
        current_id += 1

        # Update current conditioning for next controlnet in chain
        current_positive = [controlnet_apply_id, 0]
        current_negative = [controlnet_apply_id, 1]

    # Update KSampler to use the final controlnet outputs
    workflow[ksampler_id]["inputs"]["positive"] = current_positive
    workflow[ksampler_id]["inputs"]["negative"] = current_negative

    return workflow

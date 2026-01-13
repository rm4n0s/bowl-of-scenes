import copy
from typing import Any


def inject_masks_into_workflow(
    base_workflow: dict[str, Any],
    mask_files: dict[str, str],
    prompts: dict[str, str],
    clip_node_id: str = "1",
    combine_target_node_id: str = "7",
    start_node_id: int = 100,
) -> dict[str, Any]:
    """
    Inject mask loading, conditioning, and prompts into a ComfyUI workflow.

    Parameters:
    -----------
    base_workflow : Dict[str, Any]
        The base workflow in API format (dict)
    mask_files : Dict[str, str]
        Dictionary mapping color names to mask file paths
        Example: {"blue": "masks/mask_blue.png", "red": "masks/mask_red.png"}
    prompts : Dict[str, str]
        Dictionary mapping color names to their prompts
        Example: {"blue": "batman, black suit...", "red": "joker, purple suit..."}
    clip_node_id : str
        Node ID of the CheckpointLoader's CLIP output (usually "1")
    combine_target_node_id : str
        Node ID where the combined conditioning should be connected
    start_node_id : int
        Starting ID for new nodes (should be higher than existing nodes)

    Returns:
    --------
    Dict[str, Any] : New workflow with masks injected
    """

    # Deep copy the workflow to avoid modifying original
    new_workflow = copy.deepcopy(base_workflow)

    current_node_id = start_node_id
    conditioning_nodes = []

    print(f"Injecting {len(mask_files)} masks into workflow...")
    print(f"Starting from node ID: {current_node_id}\n")

    for color_name, mask_path in mask_files.items():
        if color_name not in prompts:
            print(f"⚠️  Warning: No prompt provided for '{color_name}', skipping...")
            continue

        prompt_text = prompts[color_name]

        print(f"Processing {color_name}:")
        print(f"  Mask: {mask_path}")
        print(f"  Prompt: {prompt_text[:50]}...")

        # Node 1: LoadImage for mask
        load_image_id = str(current_node_id)
        new_workflow[load_image_id] = {
            "inputs": {"image": mask_path, "upload": "image"},
            "class_type": "LoadImage",
            "_meta": {"title": f"Load Mask - {color_name}"},
        }
        print(f"  Created LoadImage node: {load_image_id}")
        current_node_id += 1

        # Node 2: CLIPTextEncode for prompt
        clip_encode_id = str(current_node_id)
        new_workflow[clip_encode_id] = {
            "inputs": {"text": prompt_text, "clip": [clip_node_id, 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": f"Prompt - {color_name}"},
        }
        print(f"  Created CLIPTextEncode node: {clip_encode_id}")
        current_node_id += 1

        # Node 3: ConditioningSetMask
        cond_mask_id = str(current_node_id)
        new_workflow[cond_mask_id] = {
            "inputs": {
                "strength": 1.0,
                "set_cond_area": "default",
                "conditioning": [clip_encode_id, 0],
                "mask": [load_image_id, 1],  # LoadImage outputs [IMAGE, MASK]
            },
            "class_type": "ConditioningSetMask",
            "_meta": {"title": f"Set Mask Area - {color_name}"},
        }
        print(f"  Created ConditioningSetMask node: {cond_mask_id}")
        current_node_id += 1

        conditioning_nodes.append(cond_mask_id)
        print("  ✅ Complete\n")

    # Create ConditioningCombine nodes to merge all conditionings
    if len(conditioning_nodes) == 0:
        print("❌ No conditioning nodes created!")
        return new_workflow
    elif len(conditioning_nodes) == 1:
        # Only one mask, connect directly
        final_conditioning_node = conditioning_nodes[0]
        print(f"Single mask detected, using node {final_conditioning_node} directly")
    else:
        # Multiple masks, combine them
        print(f"Combining {len(conditioning_nodes)} conditioning nodes...")

        # Combine in pairs (binary tree style)
        combined_id = conditioning_nodes[0]

        for i in range(1, len(conditioning_nodes)):
            combine_id = str(current_node_id)
            new_workflow[combine_id] = {
                "inputs": {
                    "conditioning_1": [combined_id, 0],
                    "conditioning_2": [conditioning_nodes[i], 0],
                },
                "class_type": "ConditioningCombine",
                "_meta": {"title": f"Combine Conditioning {i}"},
            }
            print(f"  Created ConditioningCombine node: {combine_id}")
            combined_id = combine_id
            current_node_id += 1

        final_conditioning_node = combined_id

    # Update the target node to use the combined conditioning
    print(f"\nConnecting final conditioning to node {combine_target_node_id}...")

    # This depends on your workflow structure
    # You might need to adjust based on where conditioning should go
    if combine_target_node_id in new_workflow:
        # Find the conditioning input in the target node
        target_node = new_workflow[combine_target_node_id]

        # Common patterns to update
        if "positive" in target_node["inputs"]:
            target_node["inputs"]["positive"] = [final_conditioning_node, 0]
            print("  Updated 'positive' input")
        elif "conditioning" in target_node["inputs"]:
            target_node["inputs"]["conditioning"] = [final_conditioning_node, 0]
            print("  Updated 'conditioning' input")
        else:
            print("  ⚠️  Warning: Could not find conditioning input in target node")

    print(f"\n{'=' * 60}")
    print(f"✅ Successfully injected {len(mask_files)} masks")
    print(f"   New nodes created: {current_node_id - start_node_id}")
    print(f"   Final conditioning node: {final_conditioning_node}")
    print(f"{'=' * 60}")

    return new_workflow


def inject_masks_with_auto_detect(
    base_workflow: dict[str, Any],
    mask_files: dict[str, str],
    prompts: dict[str, str],
    auto_detect_nodes: bool = True,
) -> dict[str, Any]:
    """
    Simplified version that auto-detects important nodes in the workflow.

    Parameters:
    -----------
    base_workflow : Dict[str, Any]
        The base workflow in API format
    mask_files : Dict[str, str]
        Dictionary mapping color names to mask file paths
    prompts : Dict[str, str]
        Dictionary mapping color names to their prompts
    auto_detect_nodes : bool
        If True, automatically detect checkpoint and target nodes

    Returns:
    --------
    Dict[str, Any] : New workflow with masks injected
    """

    clip_node = None
    ksampler_node = None
    controlnet_apply_node = None

    if auto_detect_nodes:
        print("Auto-detecting workflow nodes...")

        # Find CheckpointLoader
        for node_id, node_data in base_workflow.items():
            if node_data.get("class_type") == "CheckpointLoaderSimple":
                clip_node = node_id
                print(f"  Found CheckpointLoader: {node_id}")
                break

        # Find KSampler
        for node_id, node_data in base_workflow.items():
            if node_data.get("class_type") == "KSampler":
                ksampler_node = node_id
                print(f"  Found KSampler: {node_id}")
                break

        # Find ControlNetApply (if exists)
        for node_id, node_data in base_workflow.items():
            if "ControlNet" in node_data.get("class_type", ""):
                controlnet_apply_node = node_id
                print(f"  Found ControlNet: {node_id}")
                break

    if not clip_node:
        print("⚠️  Could not find CheckpointLoader, using default '1'")
        clip_node = "1"

    # Determine target node (where to connect final conditioning)
    target_node = controlnet_apply_node if controlnet_apply_node else ksampler_node

    if not target_node:
        print("⚠️  Could not find target node, using default '13'")
        target_node = "13"

    print(f"  Target node for conditioning: {target_node}\n")

    # Find highest node ID to start after
    max_node_id = max(
        [int(nid) for nid in base_workflow.keys() if nid.isdigit()], default=0
    )
    start_id = max_node_id + 10  # Leave some gap

    return inject_masks_into_workflow(
        base_workflow=base_workflow,
        mask_files=mask_files,
        prompts=prompts,
        clip_node_id=clip_node,
        combine_target_node_id=target_node,
        start_node_id=start_id,
    )

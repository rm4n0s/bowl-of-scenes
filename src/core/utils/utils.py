import re
from typing import Any


def title_with_class_type_exists(
    workflow: dict[str, Any], title: str, class_type: str
) -> bool:
    target_title = title.strip()
    for node_id, value in workflow.items():
        # Check class_type first
        node_class_type = value.get("class_type", "").strip()
        if class_type == node_class_type:
            # Then check title
            node_title = value.get("_meta", {}).get("title", "").strip()
            if target_title == node_title:
                return True

    return False


def get_title_from_class_type(workflow: dict[str, Any], class_type: str) -> list[str]:
    res = []
    for node_id, value in workflow.items():
        node_class_type = value.get("class_type", "").strip()
        if class_type == node_class_type:
            node_title = value.get("_meta", {}).get("title", "").strip()
            res.append(node_title)

    return res


def get_title_from_class_type_that_contains(
    workflow: dict[str, Any], contains_word: str
) -> list[str]:
    res = []
    for node_id, value in workflow.items():
        node_class_type = value.get("class_type", "").strip()
        if contains_word in node_class_type:
            node_title = value.get("_meta", {}).get("title", "").strip()
            res.append(node_title)

    return res


def parse_lora_tags(text: str) -> list[dict[str, Any]]:
    """
    Extract all LoRA tags from a string and convert them to a list of dictionaries.

    Args:
        text: String containing LoRA tags in format <lora:name:strength_model:strength_clip>

    Returns:
        List of dictionaries with 'name' (str), 'strength_model' (float), and 'strength_clip' (float)
    """
    pattern = r"<lora:([^:>]+):([^:>]+):([^:>]+)>"
    matches = re.findall(pattern, text)

    lora_list = []
    for match in matches:
        name, strength_model, strength_clip = match
        lora_list.append(
            {
                "name": name,
                "strength_model": float(strength_model),
                "strength_clip": float(strength_clip),
            }
        )

    return lora_list


def remove_lora_tags(text: str) -> str:
    """
    Remove all LoRA tags from a string.

    Args:
        text: String containing LoRA tags in format <lora:name:strength_model:strength_clip>

    Returns:
        String with all LoRA tags removed
    """
    pattern = r"<lora:[^:>]+:[^:>]+:[^:>]+>"
    return re.sub(pattern, "", text)

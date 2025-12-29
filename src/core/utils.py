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

import json
from typing import Any, Optional, Tuple


class LoRAInjector:
    def __init__(self, workflow: dict[str, Any]):
        self.workflow = workflow
        self.next_node_id = self._get_next_node_id()

    def _get_next_node_id(self) -> int:
        """Get the next available node ID."""
        if not self.workflow:
            return 1
        # Node IDs can be numeric or alphanumeric strings
        # Extract only numeric IDs to find the next available number
        numeric_ids = []
        for node_id in self.workflow.keys():
            try:
                numeric_ids.append(int(node_id))
            except ValueError:
                # Skip non-numeric IDs like "4a", "node_1", etc.
                continue
        return max(numeric_ids) + 1 if numeric_ids else 1

    def _find_model_nodes(self) -> list[str]:
        """Find all checkpoint loader nodes in the workflow."""
        model_nodes = []
        for node_id, node_data in self.workflow.items():
            class_type = node_data.get("class_type", "")
            if "CheckpointLoader" in class_type or "Loader" in class_type:
                model_nodes.append(node_id)
        return model_nodes

    def _find_nodes_using_model(self, model_source_id: str) -> list[Tuple[str, str]]:
        """
        Find nodes that use the model output from a given source node.
        Returns list of (node_id, input_key) tuples.
        """
        using_nodes = []
        for node_id, node_data in self.workflow.items():
            inputs = node_data.get("inputs", {})
            for input_key, input_value in inputs.items():
                # Check if this input references the model source
                if isinstance(input_value, list) and len(input_value) >= 1:
                    if input_value[0] == model_source_id:
                        using_nodes.append((node_id, input_key))
        return using_nodes

    def add_lora(
        self,
        lora_name: str,
        strength_model: float = 1.0,
        strength_clip: float = 1.0,
        insert_after_node: Optional[str] = None,
    ) -> str:
        """
        Add a LoRA node to the workflow.

        Args:
            lora_name: Name of the LoRA file (e.g., "my_lora.safetensors")
            strength_model: Model strength (default 1.0)
            strength_clip: CLIP strength (default 1.0)
            insert_after_node: Node ID to insert after. If None, finds checkpoint loader.

        Returns:
            The node ID of the created LoRA node
        """
        node_id = str(self.next_node_id)
        self.next_node_id += 1

        # If no specific node specified, find the checkpoint loader
        if insert_after_node is None:
            model_nodes = self._find_model_nodes()
            if not model_nodes:
                raise ValueError("No checkpoint loader found in workflow")
            insert_after_node = model_nodes[0]

        # Get the node we're inserting after
        source_node = self.workflow.get(insert_after_node)
        if not source_node:
            raise ValueError(f"Node {insert_after_node} not found in workflow")

        # Create the LoRA node - connect to source node BEFORE adding to workflow
        lora_node = {
            "inputs": {
                "lora_name": lora_name,
                "strength_model": strength_model,
                "strength_clip": strength_clip,
                "model": [insert_after_node, 0],  # Connect to model output
                "clip": [insert_after_node, 1],  # Connect to CLIP output
            },
            "class_type": "LoraLoader",
            "_meta": {"title": f"Load LoRA - {lora_name}"},
        }

        # Find all nodes that were using the original model/clip outputs
        # BEFORE we add the LoRA node (to avoid finding the LoRA itself)
        nodes_to_update = self._find_nodes_using_model(insert_after_node)

        # Now add the LoRA node to the workflow
        self.workflow[node_id] = lora_node

        # Redirect nodes to use the LoRA outputs instead
        # Only redirect model and clip connections (indices 0 and 1)
        for target_node_id, input_key in nodes_to_update:
            target_node = self.workflow[target_node_id]
            current_input = target_node["inputs"][input_key]

            # Only update if it's directly connected to our source node
            if isinstance(current_input, list) and len(current_input) >= 2:
                if current_input[0] == insert_after_node:
                    # Only redirect model (0) and clip (1), not VAE (2)
                    if current_input[1] in [0, 1]:
                        # Redirect to LoRA node (same output index)
                        target_node["inputs"][input_key] = [node_id, current_input[1]]

        return node_id

    def add_multiple_loras(
        self, loras: list[dict[str, Any]], insert_after_node: Optional[str] = None
    ) -> list[str]:
        """
        Add multiple LoRA nodes in sequence.

        Args:
            loras: List of dicts with keys: 'name', 'strength_model', 'strength_clip'
            insert_after_node: Starting node. If None, finds checkpoint loader.

        Returns:
            List of created LoRA node IDs
        """
        created_nodes = []
        current_node = insert_after_node

        for lora_config in loras:
            lora_name = lora_config["name"]
            strength_model = lora_config.get("strength_model", 1.0)
            strength_clip = lora_config.get("strength_clip", 1.0)

            node_id = self.add_lora(
                lora_name, strength_model, strength_clip, insert_after_node=current_node
            )
            created_nodes.append(node_id)
            current_node = node_id  # Chain LoRAs together

        return created_nodes

    def save(self, output_path: str):
        """Save the modified workflow to a file."""
        with open(output_path, "w") as f:
            json.dump(self.workflow, f, indent=2)

    def get_workflow(self) -> dict:
        """Get the modified workflow as a dictionary."""
        return self.workflow

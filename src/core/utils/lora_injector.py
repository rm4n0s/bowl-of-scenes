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

    def _detect_workflow_type(self) -> str:
        """
        Detect the type of workflow based on loader nodes present.

        Returns:
            'checkpoint' - Standard workflow with CheckpointLoader (SD, SDXL, etc.)
            'split' - Split workflow with separate UNETLoader + CLIPLoader (Z-Image, Flux, etc.)
            'unknown' - Could not determine workflow type
        """
        has_checkpoint_loader = False
        has_unet_loader = False
        has_clip_loader = False

        for node_data in self.workflow.values():
            class_type = node_data.get("class_type", "")
            if "CheckpointLoader" in class_type:
                has_checkpoint_loader = True
            if class_type == "UNETLoader":
                has_unet_loader = True
            if class_type == "CLIPLoader":
                has_clip_loader = True

        if has_checkpoint_loader:
            return "checkpoint"
        elif has_unet_loader:
            return "split"
        return "unknown"

    def _find_model_nodes(self) -> list[str]:
        """Find all checkpoint loader nodes in the workflow."""
        model_nodes = []
        for node_id, node_data in self.workflow.items():
            class_type = node_data.get("class_type", "")
            if "CheckpointLoader" in class_type:
                model_nodes.append(node_id)
        return model_nodes

    def _find_unet_loader(self) -> Optional[str]:
        """Find the UNETLoader node (used in Z-Image, Flux, etc.)."""
        for node_id, node_data in self.workflow.items():
            if node_data.get("class_type") == "UNETLoader":
                return node_id
        return None

    def _find_clip_loader(self) -> Optional[str]:
        """Find the CLIPLoader node (used in Z-Image, Flux, etc.)."""
        for node_id, node_data in self.workflow.items():
            if node_data.get("class_type") == "CLIPLoader":
                return node_id
        return None

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

    def _find_nodes_using_output(
        self, source_id: str, output_index: int
    ) -> list[Tuple[str, str]]:
        """
        Find nodes that use a specific output from a given source node.
        Returns list of (node_id, input_key) tuples.
        """
        using_nodes = []
        for node_id, node_data in self.workflow.items():
            inputs = node_data.get("inputs", {})
            for input_key, input_value in inputs.items():
                if isinstance(input_value, list) and len(input_value) >= 2:
                    if input_value[0] == source_id and input_value[1] == output_index:
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
        Automatically detects workflow type and uses appropriate LoRA loader.

        Args:
            lora_name: Name of the LoRA file (e.g., "my_lora.safetensors")
            strength_model: Model strength (default 1.0)
            strength_clip: CLIP strength (default 1.0)
            insert_after_node: Node ID to insert after. If None, auto-detects.

        Returns:
            The node ID of the created LoRA node
        """
        workflow_type = self._detect_workflow_type()

        if workflow_type == "split":
            return self._add_lora_split_workflow(
                lora_name, strength_model, strength_clip, insert_after_node
            )
        elif workflow_type == "checkpoint":
            return self._add_lora_checkpoint_workflow(
                lora_name, strength_model, strength_clip, insert_after_node
            )
        else:
            raise ValueError(
                "Could not detect workflow type. "
                "Expected CheckpointLoader or UNETLoader node."
            )

    def _add_lora_split_workflow(
        self,
        lora_name: str,
        strength_model: float,
        strength_clip: float,
        insert_after_node: Optional[str],
    ) -> str:
        """
        Add LoRA to a split workflow (Z-Image, Flux, etc.) that uses
        separate UNETLoader and CLIPLoader nodes.

        Uses LoraLoaderModelOnly since CLIP is loaded separately.
        """
        node_id = str(self.next_node_id)
        self.next_node_id += 1

        # Find the UNET loader if no specific node specified
        if insert_after_node is None:
            insert_after_node = self._find_unet_loader()
            if not insert_after_node:
                raise ValueError("No UNETLoader found in workflow")

        source_node = self.workflow.get(insert_after_node)
        if not source_node:
            raise ValueError(f"Node {insert_after_node} not found in workflow")

        # Determine if we're inserting after UNETLoader or another LoRA
        source_class = source_node.get("class_type", "")

        # Create LoRA node - for split workflows, use LoraLoaderModelOnly
        # since CLIP is handled by a separate CLIPLoader
        lora_node = {
            "inputs": {
                "lora_name": lora_name,
                "strength_model": strength_model,
                "model": [insert_after_node, 0],  # Connect to model output
            },
            "class_type": "LoraLoaderModelOnly",
            "_meta": {"title": f"Load LoRA - {lora_name}"},
        }

        # Find nodes using the model output BEFORE adding LoRA node
        nodes_to_update = self._find_nodes_using_output(insert_after_node, 0)

        # Add the LoRA node
        self.workflow[node_id] = lora_node

        # Redirect model connections to use LoRA output
        for target_node_id, input_key in nodes_to_update:
            if target_node_id == node_id:
                continue  # Don't redirect the LoRA node itself
            target_node = self.workflow[target_node_id]
            target_node["inputs"][input_key] = [node_id, 0]

        return node_id

    def _add_lora_checkpoint_workflow(
        self,
        lora_name: str,
        strength_model: float,
        strength_clip: float,
        insert_after_node: Optional[str],
    ) -> str:
        """
        Add LoRA to a standard checkpoint workflow (SD, SDXL, etc.) that uses
        CheckpointLoader which outputs MODEL, CLIP, and VAE together.

        Uses LoraLoader which handles both MODEL and CLIP.
        """
        node_id = str(self.next_node_id)
        self.next_node_id += 1

        # If no specific node specified, find the checkpoint loader
        if insert_after_node is None:
            model_nodes = self._find_model_nodes()
            if not model_nodes:
                raise ValueError("No checkpoint loader found in workflow")
            insert_after_node = model_nodes[0]

        source_node = self.workflow.get(insert_after_node)
        if not source_node:
            raise ValueError(f"Node {insert_after_node} not found in workflow")

        # Create the LoRA node
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

        # Find all nodes using model/clip outputs BEFORE adding LoRA
        nodes_to_update = self._find_nodes_using_model(insert_after_node)

        # Add the LoRA node
        self.workflow[node_id] = lora_node

        # Redirect nodes to use LoRA outputs instead
        for target_node_id, input_key in nodes_to_update:
            if target_node_id == node_id:
                continue
            target_node = self.workflow[target_node_id]
            current_input = target_node["inputs"][input_key]

            if isinstance(current_input, list) and len(current_input) >= 2:
                if current_input[0] == insert_after_node:
                    # Only redirect model (0) and clip (1), not VAE (2)
                    if current_input[1] in [0, 1]:
                        target_node["inputs"][input_key] = [node_id, current_input[1]]

        return node_id

    def add_multiple_loras(
        self, loras: list[dict[str, Any]], insert_after_node: Optional[str] = None
    ) -> list[str]:
        """
        Add multiple LoRA nodes in sequence.

        Args:
            loras: List of dicts with keys: 'name', 'strength_model', 'strength_clip'
            insert_after_node: Starting node. If None, auto-detects based on workflow type.

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

    def get_workflow_info(self) -> dict[str, Any]:
        """Get information about the current workflow."""
        workflow_type = self._detect_workflow_type()
        info = {
            "workflow_type": workflow_type,
            "node_count": len(self.workflow),
            "next_node_id": self.next_node_id,
        }

        if workflow_type == "split":
            info["unet_loader"] = self._find_unet_loader()
            info["clip_loader"] = self._find_clip_loader()
            info["lora_type"] = "LoraLoaderModelOnly"
        elif workflow_type == "checkpoint":
            info["checkpoint_loaders"] = self._find_model_nodes()
            info["lora_type"] = "LoraLoader"

        return info

    def save(self, output_path: str):
        """Save the modified workflow to a file."""
        with open(output_path, "w") as f:
            json.dump(self.workflow, f, indent=2)

    def get_workflow(self) -> dict:
        """Get the modified workflow as a dictionary."""
        return self.workflow

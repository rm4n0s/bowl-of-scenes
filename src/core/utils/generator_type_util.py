from dataclasses import asdict, dataclass

from src.controllers.ctrl_types import (
    GeneratorOutputType,
    ImageAttributes,
    ThreeDAttributes,
    VideoAttributes,
)


@dataclass
class GeneratorOutputAnalysis:
    generator_output_type: GeneratorOutputType
    attributes: ImageAttributes | VideoAttributes | ThreeDAttributes
    node_class_type: str
    node_title: str

    def to_dict(self) -> dict:
        return {
            "generator_output_type": self.generator_output_type,
            "attributes": asdict(self.attributes),
            "node_class_type": self.node_class_type,
            "node_title": self.node_title,
        }


OUTPUT_NODES = {
    # Images
    "SaveImage": {"generator_output_type": "image", "file_type": "png"},
    "PreviewImage": {"generator_output_type": "image", "file_type": "png"},
    "SaveAnimatedWEBP": {"generator_output_type": "image", "file_type": "webp"},
    "SaveAnimatedPNG": {"generator_output_type": "image", "file_type": "apng"},
    "Image Save": {"generator_output_type": "image", "file_type": None},
    "SaveImageExtended": {"generator_output_type": "image", "file_type": None},
    "JWImageSave": {"generator_output_type": "image", "file_type": None},
    # Video
    "VHS_VideoCombine": {"generator_output_type": "video", "file_type": None},
    # 3D
    "SaveGLB": {"generator_output_type": "3d", "file_type": "glb"},
    "Save3DModel": {"generator_output_type": "3d", "file_type": None},
}

# ── Dimension nodes in priority order ────────────────────────────────────────
# Excluded: ImageScaleBy (uses scale_by ratio, not explicit w/h)
DIMENSION_NODE_PRIORITY = [
    # Latent creators — most authoritative (primary generation resolution)
    "EmptyLatentImage",
    "EmptySD3LatentImage",
    "EmptyLatentImageSD3",
    "EmptyMochiLatentVideo",
    "EmptyHunyuanLatentVideo",
    "EmptyLTXVLatentVideo",
    "EmptyWanLatentVideo",
    "EmptyCogVideoLatentVideo",
    "EmptyFluxLatentVideo",
    # Resize/upscale nodes — secondary (may override latent size)
    "ImageScale",
    "ImageResize",
    "LatentUpscale",
]

# ── Nodes that carry frame/duration info for video ────────────────────────────
VIDEO_FRAME_NODES = [
    "EmptyMochiLatentVideo",
    "EmptyHunyuanLatentVideo",
    "EmptyLTXVLatentVideo",
    "EmptyWanLatentVideo",
    "EmptyCogVideoLatentVideo",
    "EmptyFluxLatentVideo",
]


def _get_dimensions(workflow: dict) -> tuple[int, int] | None:
    """Find width/height from the highest-priority dimension node."""
    found = []
    for node in workflow.values():
        class_type = node.get("class_type", "")
        if class_type not in DIMENSION_NODE_PRIORITY:
            continue
        inputs = node.get("inputs", {})
        width = inputs.get("width")
        height = inputs.get("height")
        if isinstance(width, list) or isinstance(height, list):
            continue
        if width and height:
            found.append(
                (
                    DIMENSION_NODE_PRIORITY.index(class_type),
                    int(width),
                    int(height),
                )
            )
    if not found:
        return None
    found.sort(key=lambda x: x[0])
    _, width, height = found[0]
    return width, height


def _build_image_attributes(
    workflow: dict, file_type: str | None, dims: tuple | None
) -> ImageAttributes:
    attrs = ImageAttributes(
        file_type=file_type,
        width=dims[0] if dims else None,
        height=dims[1] if dims else None,
    )
    for node in workflow.values():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        if class_type in (
            "EmptyLatentImage",
            "EmptySD3LatentImage",
            "EmptyLatentImageSD3",
        ):
            val = inputs.get("batch_size")
            if val and not isinstance(val, list):
                attrs.batch_size = int(val)

        if class_type in ("KSampler", "KSamplerAdvanced"):
            for key in ("steps", "cfg", "sampler_name", "scheduler", "denoise", "seed"):
                val = inputs.get(key)
                if val is not None and not isinstance(val, list):
                    setattr(attrs, key, val)

    return attrs


def _build_video_attributes(
    workflow: dict, file_type: str | None, dims: tuple | None
) -> VideoAttributes:
    attrs = VideoAttributes(
        file_type=file_type,
        width=dims[0] if dims else None,
        height=dims[1] if dims else None,
    )
    for node in workflow.values():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        if class_type == "VHS_VideoCombine":
            val = inputs.get("frame_rate")
            if val and not isinstance(val, list):
                attrs.fps = val

        if class_type in VIDEO_FRAME_NODES:
            for key in ("num_frames", "video_length", "length"):
                val = inputs.get(key)
                if val and not isinstance(val, list):
                    attrs.num_frames = int(val)
                    break

    if attrs.fps and attrs.num_frames:
        attrs.duration_seconds = round(attrs.num_frames / attrs.fps, 2)

    return attrs


def _build_3d_attributes(file_type: str | None) -> ThreeDAttributes:
    return ThreeDAttributes(file_type=file_type)


def _resolve_file_type(static_file_type: str | None, output_inputs: dict) -> str | None:
    if static_file_type:
        return static_file_type
    ext = output_inputs.get("extension") or output_inputs.get("format")
    if ext:
        return ext.split("/")[-1].lower() if "/" in ext else ext.lower()
    return None


def get_generator_output_type(workflow: dict) -> GeneratorOutputAnalysis:
    """
    Analyze a ComfyUI API format workflow.

    Returns a GeneratorOutputAnalysis dataclass with:
        .generator_output_type  →  "image" | "video" | "3d" | "unknown"
        .attributes    →  ImageAttributes | VideoAttributes | ThreeDAttributes
    """
    # ── 1. Detect output node ─────────────────────────────────────────────────
    generator_output_type = GeneratorOutputType.UNKNOWN
    static_ftype = None
    output_inputs = {}
    node_class_type = ""
    node_title = ""
    for node in workflow.values():
        node_class_type = node.get("class_type", "")
        if node_class_type in OUTPUT_NODES:
            info = OUTPUT_NODES[node_class_type]
            generator_output_type = GeneratorOutputType(info["generator_output_type"])
            static_ftype = info["file_type"]
            output_inputs = node.get("inputs", {})
            node_title = node.get("_meta", {}).get("title", "").strip()
            break

    # ── 2. Resolve file_type & dimensions ─────────────────────────────────────
    file_type = _resolve_file_type(static_ftype, output_inputs)
    dims = _get_dimensions(workflow)

    # ── 3. Build typed attributes ─────────────────────────────────────────────
    if generator_output_type == GeneratorOutputType.IMAGE:
        attributes = _build_image_attributes(workflow, file_type, dims)
    elif generator_output_type == GeneratorOutputType.VIDEO:
        attributes = _build_video_attributes(workflow, file_type, dims)
    elif generator_output_type == GeneratorOutputType.THREE_D:
        attributes = _build_3d_attributes(file_type)
    else:
        raise Exception("Couldn't find the generator's type output")

    return GeneratorOutputAnalysis(
        generator_output_type=generator_output_type,
        attributes=attributes,
        node_class_type=node_class_type,
        node_title=node_title,
    )


def update_workflow_ksampler(workflow: dict, attributes: ImageAttributes) -> dict:
    """
    Updates the KSampler and latent image nodes in a ComfyUI API workflow
    with values from ImageAttributes.
    Only updates fields that are not None in the attributes.

    Args:
        workflow:   ComfyUI API format workflow dict
        attributes: ImageAttributes dataclass with values to apply

    Returns:
        Updated workflow dict (mutates in place and returns it)

    Raises:
        ValueError: If no KSampler node is found in the workflow
    """
    KSAMPLER_FIELD_MAP = {
        "steps": "steps",
        "cfg": "cfg",
        "sampler_name": "sampler_name",
        "scheduler": "scheduler",
        "denoise": "denoise",
        "seed": "seed",
    }

    # Latent image nodes that hold width/height
    LATENT_IMAGE_NODES = (
        "EmptyLatentImage",
        "EmptySD3LatentImage",
        "EmptyLatentImageSD3",
    )

    ksampler_found = False

    for node in workflow.values():
        class_type = node.get("class_type", "")

        # ── KSampler ──────────────────────────────────────────────────────────
        if class_type in ("KSampler", "KSamplerAdvanced"):
            ksampler_found = True
            inputs = node["inputs"]
            for attr_field, ksampler_key in KSAMPLER_FIELD_MAP.items():
                value = getattr(attributes, attr_field, None)
                if value is not None:
                    inputs[ksampler_key] = value

        # ── Latent image (width/height) ───────────────────────────────────────
        if class_type in LATENT_IMAGE_NODES:
            inputs = node["inputs"]
            if attributes.width is not None:
                inputs["width"] = attributes.width
            if attributes.height is not None:
                inputs["height"] = attributes.height

    if not ksampler_found:
        raise ValueError("No KSampler or KSamplerAdvanced node found in workflow.")

    return workflow

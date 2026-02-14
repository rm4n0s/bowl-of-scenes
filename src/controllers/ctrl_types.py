import enum
from dataclasses import dataclass
from typing import Any

from nicegui.elements.upload_files import FileUpload
from yet_another_comfy_client import YetAnotherComfyClient


class ControlNetType(enum.Enum):
    OPENPOSE = "openpose"
    DWPOSE = "dwpose"
    TILE = "tile"
    CANNY = "canny"
    MIDAS = "midas"
    DEPTH = "depth"
    LINEART = "lineart"
    SOFTEDGE = "softedge"
    SCRIBBLE = "scribble"
    NORMAL = "normal"


@dataclass
class ControlNetConfig:
    type_of_controlnet: ControlNetType
    image_path: str
    is_reference: bool  # True = preprocess the image, False = use image directly
    model_pattern: str  # e.g., "control_v11p_sd15_canny.safetensors" or "diffusers_xl_canny_mid.safetensors"
    strength: float  # ControlNet strength (0.0 to 2.0, typically 0.5-1.5)

    def __post_init__(self):
        """Automatically convert string to enum if needed"""
        if isinstance(self.type_of_controlnet, str):
            self.type_of_controlnet = ControlNetType(self.type_of_controlnet)


# Mapping of ControlNet types to their preprocessor class
CONTROLNET_PREPROCESSORS = {
    ControlNetType.OPENPOSE: "OpenposePreprocessor",
    ControlNetType.DWPOSE: "DWPreprocessor",
    ControlNetType.CANNY: "CannyEdgePreprocessor",
    ControlNetType.MIDAS: "MidasDepthMapPreprocessor",
    ControlNetType.DEPTH: "DepthAnythingPreprocessor",
    ControlNetType.TILE: None,  # Tile usually doesn't need preprocessing
    ControlNetType.LINEART: "LineArtPreprocessor",
    ControlNetType.SOFTEDGE: "HEDPreprocessor",
    ControlNetType.SCRIBBLE: "ScribblePreprocessor",
    ControlNetType.NORMAL: "BAE-NormalMapPreprocessor",
}


class JobStatus(enum.StrEnum):
    WAITING = "waiting"
    PROCESSING = "processing"
    FINISHED = "finished"


@dataclass
class CoordinatedRegion:
    width: int
    height: int
    x: int
    y: int


@dataclass
class RegionPrompt:
    keyword: str
    mask_file: str | None
    coordinates: CoordinatedRegion | None
    prompt: str
    loras: list[dict[str, Any]]


@dataclass
class Lora:
    name: str
    strength_model: float
    strength_clip: float


@dataclass
class CoordinatedRegionKeyword:
    keyword: str
    width: int
    height: int
    x: int
    y: int


@dataclass
class IPAdapter:
    image_file: str
    weight: float
    weight_type: str
    start_at: float
    end_at: float
    clip_vision_model: str
    model_name: str


@dataclass
class MaskRegionImages:
    reference_path: str
    folder_path: str
    mask_files: dict[str, str]


@dataclass
class CategoryInput:
    name: str


@dataclass
class CategoryOutput:
    id: int
    name: str


@dataclass
class GroupInput:
    name: str
    description: str
    code_name: str
    category_id: int
    use_lora: bool
    use_controlnet: bool
    use_ip_adapter: bool
    use_mask_region: bool
    use_coordinates_region: bool
    thumbnail_image: FileUpload | None


@dataclass
class GroupOutput:
    id: int
    name: str
    description: str
    code_name: str
    category_id: int
    use_lora: bool
    use_controlnet: bool
    use_ip_adapter: bool
    use_mask_region: bool
    use_coordinates_region: bool
    thumbnail_image: str | None
    show_thumbnail_image: str | None


@dataclass
class ItemIPAdapterInput:
    reference_image: FileUpload
    weight: float
    weight_type: str
    start_at: float
    end_at: float
    clip_vision_model: str
    model_name: str


@dataclass
class ItemIPAdapterOutput:
    reference_image: str
    show_reference_image: str
    weight: float
    weight_type: str
    start_at: float
    end_at: float
    clip_vision_model: str
    model_name: str


@dataclass
class ControlNetConfigInput:
    type_of_controlnet: ControlNetType
    image_path: (
        FileUpload | None
    )  # if None then all controlnet input will not be processed
    is_reference: bool
    model_pattern: str
    strength: float


@dataclass
class ItemInput:
    group_id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    lora: str | None
    controlnets: list[ControlNetConfigInput]
    coordinated_regions: str | None
    ipadapter: ItemIPAdapterInput | None
    mask_region_reference_image: FileUpload | None
    thumbnail_image: FileUpload | None


@dataclass
class ItemOutput:
    id: int
    group_id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    lora: str | None
    controlnets: list[ControlNetConfig] | None
    coordinated_regions: str | None
    coordinated_region_keys: str | None
    ipadapter: ItemIPAdapterOutput | None
    mask_region_images: MaskRegionImages | None
    mask_region_images_keys: str | None
    thumbnail_image: str | None
    show_thumbnail_image: str | None


@dataclass
class ReplInput:
    generator_code_name: str
    server_code_name: str
    prompt_positive: str
    prompt_negative: str
    group_item_code_names: str
    reference_ipadapter_img: FileUpload | None
    lora_list: str


@dataclass
class JobOutput:
    id: int
    project_id: int
    command_id: int
    group_item_id_list: list[dict[str, Any]]
    code_str: str
    server_code_name: str
    server_host: str
    status: JobStatus
    generator_code_name: str | None
    fixer_code_name: str | None
    comfyui_prompt_id: str | None
    prompt_positive: str
    prompt_negative: str
    ipadapter_list: list[dict[str, Any]]
    region_prompts: dict[str, RegionPrompt] | None
    lora_list: list[dict[str, Any]]
    result_img: str
    show_result_img: str


@dataclass
class ServerData:
    id: int
    host: str
    code_name: str
    client: YetAnotherComfyClient


@dataclass
class ProjectInput:
    name: str


@dataclass
class ProjectOutput:
    id: int
    name: str


class StatusEnum(enum.StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass
class ServerInput:
    name: str
    host: str
    code_name: str
    is_local: bool


@dataclass
class ServerOutput:
    id: int
    name: str
    host: str
    code_name: str
    is_local: bool
    status: StatusEnum


@dataclass
class GeneratorInput:
    name: str
    code_name: str
    workflow_json: dict[str, Any]
    positive_prompt_title: str | None
    negative_prompt_title: str | None
    save_image_title: str


@dataclass
class GeneratorOutput:
    id: int
    name: str
    code_name: str
    workflow_json: dict[str, Any]
    positive_prompt_title: str | None
    negative_prompt_title: str | None
    save_image_title: str


@dataclass
class FixerInput:
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    positive_prompt_title: str
    negative_prompt_title: str
    load_image_title: str
    save_image_title: str
    workflow_json: dict[str, Any]


@dataclass
class FixerOutput:
    id: int
    name: str
    code_name: str
    positive_prompt: str
    negative_prompt: str
    positive_prompt_title: str
    negative_prompt_title: str
    load_image_title: str
    save_image_title: str
    workflow_json: dict[str, Any]

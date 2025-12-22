from dataclasses import dataclass


@dataclass
class GroupInput:
    name: str
    description: str
    code_name: str
    category_id: int
    use_loras: bool
    use_controlnet: bool
    use_ip_adapter: bool
    thumbnail_image: str

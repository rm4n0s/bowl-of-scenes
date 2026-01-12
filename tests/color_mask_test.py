import os

from src.core.utils.masking import (
    create_conditioning_masks,
)


def test_create_conditioning_masks():
    create_conditioning_masks(
        "tests/testdata/color-mask.png",
        output_dir="/tmp/masks",
        ignore_colors=[(255, 255, 255)],
    )
    assert os.path.exists("/tmp/masks")
    assert os.path.exists("/tmp/masks/mask_red.png")
    assert os.path.exists("/tmp/masks/mask_blue.png")
    assert not os.path.exists("/tmp/masks/mask_white.png")

import os

from src.core.utils.auto_masking import auto_create_masks


def test_create_conditioning_masks():
    auto_create_masks(
        "tests/testdata/color-mask.png",
        "/tmp/masks",
    )
    assert os.path.exists("/tmp/masks")
    assert os.path.exists("/tmp/masks/mask_red.png")
    assert os.path.exists("/tmp/masks/mask_blue.png")
    assert not os.path.exists("/tmp/masks/mask_white.png")

    mask_paths = auto_create_masks(
        "tests/testdata/poeple-street-scene.jpg", "/tmp/masks"
    )
    print(mask_paths)
    count = 1
    for k, v in mask_paths.items():
        assert k == "person_" + str(count)
        assert os.path.exists(v)
        count += 1

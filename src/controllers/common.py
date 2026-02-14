import os
import shutil

from src.controllers.ctrl_types import ControlNetConfig, IPAdapter, MaskRegionImages
from src.db.records import ItemRecord


async def delete_item_files(item: ItemRecord):
    if item.ipadapter is not None:
        ipadapter = IPAdapter(**item.ipadapter)
        if os.path.exists(ipadapter.image_file):
            os.remove(ipadapter.image_file)

    if item.mask_region_images is not None:
        mask_region_images = MaskRegionImages(**item.mask_region_images)
        if os.path.exists(mask_region_images.reference_path):
            os.remove(mask_region_images.reference_path)

        if os.path.exists(mask_region_images.folder_path):
            shutil.rmtree(mask_region_images.folder_path)

    if item.controlnets is not None:
        for v in item.controlnets:
            cn = ControlNetConfig(**v)
            if os.path.exists(cn.image_path):
                os.remove(cn.image_path)

import os
import shutil

from src.db.records import ItemRecord
from src.db.records.item_rec import IPAdapter, MaskRegionImages


async def delete_item_files(item: ItemRecord):
    if item.ipadapter is not None:
        ipadapter = IPAdapter(**item.ipadapter)
        if os.path.exists(ipadapter.image_file):
            os.remove(ipadapter.image_file)

    if item.controlnet_reference_image is not None:
        if os.path.exists(item.controlnet_reference_image):
            os.remove(item.controlnet_reference_image)

    if item.mask_region_images is not None:
        mask_region_images = MaskRegionImages(**item.mask_region_images)
        if os.path.exists(mask_region_images.reference_path):
            os.remove(mask_region_images.reference_path)

        if os.path.exists(mask_region_images.folder_path):
            shutil.rmtree(mask_region_images.folder_path)

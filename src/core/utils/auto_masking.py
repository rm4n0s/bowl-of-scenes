import os

import cv2
import numpy as np
from ultralytics import YOLO  # pyright: ignore[reportPrivateImportUsage]


def auto_create_masks(input_image_path: str, output_dir: str) -> dict[str, str]:
    """
    Analyzes the input image and decides whether to use color detection or person segmentation.
    Saves appropriate mask files to the specified output directory.
    Returns a list of paths to the generated mask files.
    """
    img = cv2.imread(input_image_path)
    if img is None:
        raise ValueError(f"Could not load image from {input_image_path}")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Get unique colors excluding background (assuming white [255,255,255])
    pixels = img.reshape(-1, 3)
    unique_colors = np.unique(pixels, axis=0)
    bg_color = np.array([255, 255, 255])
    non_bg_colors = unique_colors[~np.all(unique_colors == bg_color, axis=1)]
    num_unique_non_bg = len(non_bg_colors)

    mask_paths = {}

    if num_unique_non_bg <= 10:
        # Color detection method
        color_to_name = {
            (255, 0, 0): "red",
            (0, 255, 0): "green",
            (0, 0, 255): "blue",
            (255, 255, 0): "yellow",
            (255, 0, 255): "magenta",
            (0, 255, 255): "cyan",
            (128, 0, 0): "maroon",
            (0, 128, 0): "dark_green",
            (0, 0, 128): "navy",
            (128, 128, 0): "olive",
            (255, 165, 0): "orange",
            (128, 0, 128): "purple",
            (255, 192, 203): "pink",
            (165, 42, 42): "brown",
            (128, 128, 128): "gray",
            # Add more if needed
        }

        for color in non_bg_colors:
            # Create binary mask
            mask = np.all(img == color, axis=-1).astype(np.uint8) * 255
            # Name the mask
            color_tuple = tuple(color.tolist())
            color_name = color_to_name.get(
                color_tuple, f"color_{color[0]}_{color[1]}_{color[2]}"
            )
            mask_filename = f"mask_{color_name}.png"
            mask_path = os.path.join(output_dir, mask_filename)
            cv2.imwrite(mask_path, mask)
            mask_paths[color_name] = mask_path

    else:
        # Person segmentation method
        model = YOLO(
            "yolov8n-seg.pt"
        )  # Use a segmentation model; can change to larger like 'yolov8m-seg.pt'
        results = model(img)

        person_masks = []
        if results[0].masks is not None:
            for i, mask_tensor in enumerate(results[0].masks.data):
                if results[0].boxes.cls[i] == 0:  # Class 0 is 'person' in COCO
                    mask_np = (mask_tensor.cpu().numpy() * 255).astype(np.uint8)
                    # Ensure mask is same size as image
                    if mask_np.shape != img.shape[:2]:
                        mask_np = cv2.resize(mask_np, (img.shape[1], img.shape[0]))
                    person_masks.append(mask_np)

        # Create color-coded image
        color_coded = np.ones_like(img) * 255  # White background
        colors = [
            (0, 0, 255),  # blue
            (0, 255, 0),  # green
            (255, 0, 0),  # red
            (0, 255, 255),  # yellow
            (255, 0, 255),  # magenta
            (255, 255, 0),  # cyan
            (128, 0, 0),
            (0, 128, 0),
            (0, 0, 128),
            (128, 128, 0),
            (255, 165, 0),
            (128, 0, 128),
            (255, 192, 203),
            (165, 42, 42),
            (128, 128, 128),
            # Add more if needed
        ]

        for i, mask in enumerate(person_masks):
            color = colors[i % len(colors)]
            color_coded[mask > 127] = color  # Threshold to apply color

        color_coded_path = os.path.join(output_dir, "color_coded.png")
        cv2.imwrite(color_coded_path, color_coded)

        # Save individual binary masks
        for i, mask in enumerate(person_masks):
            key = f"person_{i + 1}"
            mask_filename = f"mask_{key}.png"
            mask_path = os.path.join(output_dir, mask_filename)
            cv2.imwrite(mask_path, mask)
            mask_paths[key] = mask_path

    return mask_paths

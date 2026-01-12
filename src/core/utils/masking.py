import os

import numpy as np
from PIL import Image


def rgb_to_name(rgb):
    """Convert RGB tuple to a readable color name"""
    color_names = {
        (255, 0, 0): "red",
        (0, 255, 0): "green",
        (0, 0, 255): "blue",
        (255, 255, 0): "yellow",
        (255, 0, 255): "magenta",
        (0, 255, 255): "cyan",
        (255, 165, 0): "orange",
        (128, 0, 128): "purple",
        (255, 192, 203): "pink",
        (165, 42, 42): "brown",
        (128, 128, 128): "gray",
        (255, 255, 255): "white",
        (0, 0, 0): "black",
    }

    # Find closest color name
    min_distance = float("inf")
    closest_name = f"color_{rgb[0]}_{rgb[1]}_{rgb[2]}"

    for known_rgb, name in color_names.items():
        # FIX: Cast to int to prevent overflow
        distance = sum((int(a) - int(b)) ** 2 for a, b in zip(rgb, known_rgb))
        if distance < min_distance:
            min_distance = distance
            closest_name = name

    # If very close to a known color (threshold), use its name
    if min_distance < 1000:  # Adjust threshold as needed
        return closest_name
    else:
        # Use RGB values for unknown colors
        return f"color_{rgb[0]}_{rgb[1]}_{rgb[2]}"


def create_conditioning_masks(
    input_image_path: str,
    output_dir: str,
    tolerance: int = 10,
    ignore_colors: list[tuple[int, int, int]] | None = None,
):
    """
    Automatically detect all colors in image and create conditioning mask for each one.

    Parameters:
    -----------
    input_image_path : str
        Path to the input color-coded image
    output_dir : str
        Directory where mask images will be saved
    tolerance : int
        Color similarity tolerance (0-255). Colors within this range are considered the same.
    ignore_colors : list of tuples
        List of RGB colors to ignore (e.g., [(255, 255, 255)] to ignore white background)

    Returns:
    --------
    dict : Dictionary mapping color names to mask file paths
    """

    if ignore_colors is None:
        ignore_colors = []

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load the image
    img = Image.open(input_image_path).convert("RGB")
    img_array = np.array(img)

    # Get image dimensions
    height, width = img_array.shape[:2]

    print(f"Analyzing image: {width}x{height} pixels")
    print("Detecting colors automatically...")

    # Find unique colors by sampling
    unique_colors = {}

    # First pass: detect distinct colors
    for y in range(height):
        for x in range(width):
            # FIX: Convert to tuple of ints (not uint8)
            pixel_color = (
                int(img_array[y, x, 0]),
                int(img_array[y, x, 1]),
                int(img_array[y, x, 2]),
            )

            # Check if should ignore this color
            should_ignore = False
            for ignore_color in ignore_colors:
                # FIX: Cast to int to prevent overflow
                if all(
                    abs(int(pixel_color[i]) - int(ignore_color[i])) <= tolerance
                    for i in range(3)
                ):
                    should_ignore = True
                    break

            if should_ignore:
                continue

            # Check if this color is similar to any already found
            found_similar = False
            for existing_color in list(unique_colors.keys()):
                # FIX: Cast to int to prevent overflow
                if all(
                    abs(int(pixel_color[i]) - int(existing_color[i])) <= tolerance
                    for i in range(3)
                ):
                    unique_colors[existing_color].append((x, y))
                    found_similar = True
                    break

            if not found_similar:
                unique_colors[pixel_color] = [(x, y)]

    print(f"Found {len(unique_colors)} unique colors (excluding ignored colors)")

    # Create mask for each color
    mask_files = {}

    for i, (color, pixels) in enumerate(unique_colors.items(), 1):
        # Create color name
        color_name = rgb_to_name(color)

        print(f"\nProcessing color {i}/{len(unique_colors)}: {color_name} RGB{color}")
        print(f"  Pixels with this color: {len(pixels)}")

        # Create blank (black) mask
        mask = np.zeros((height, width), dtype=np.uint8)

        # Set pixels of this color to white (255)
        for x, y in pixels:
            mask[y, x] = 255

        # Convert to PIL Image
        mask_img = Image.fromarray(mask, mode="L")

        # Generate filename
        output_filename = f"mask_{color_name}.png"
        output_path = os.path.join(output_dir, output_filename)

        # Save mask
        mask_img.save(output_path)
        print(f"  ✅ Saved: {output_path}")

        mask_files[color_name] = output_path

    print(f"\n{'=' * 60}")
    print(f"✅ Successfully created {len(mask_files)} mask images")
    print(f"   Output directory: {output_dir}/")
    print(f"{'=' * 60}")

    return mask_files

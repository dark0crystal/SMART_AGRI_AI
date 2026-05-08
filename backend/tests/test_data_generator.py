"""
Test data generators for creating artificial test images and descriptions.
"""

from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFilter
import random


def generate_healthy_lemon_image(
    width: int = 256, height: int = 256, filename: Optional[str] = None
) -> Image.Image:
    """Generate an artificial image representing a healthy lemon tree."""
    img = Image.new("RGB", (width, height), color=(200, 220, 180))  # Light green background
    draw = ImageDraw.Draw(img)

    # Draw tree trunk (brown)
    trunk_x = width // 2
    trunk_y = height // 2
    draw.rectangle(
        [trunk_x - 5, trunk_y + 30, trunk_x + 5, trunk_y + 100],
        fill=(101, 67, 33),
    )

    # Draw healthy green foliage (multiple circles)
    foliage_color = (34, 139, 34)  # Dark green
    for _ in range(8):
        x = random.randint(trunk_x - 60, trunk_x + 60)
        y = random.randint(trunk_y - 80, trunk_y + 30)
        r = random.randint(25, 40)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=foliage_color)

    # Draw yellow lemons
    lemon_color = (255, 215, 0)  # Gold
    for _ in range(4):
        x = random.randint(trunk_x - 50, trunk_x + 50)
        y = random.randint(trunk_y - 70, trunk_y + 20)
        draw.ellipse([x - 8, y - 8, x + 8, y + 8], fill=lemon_color)

    # Add slight blur for realism
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    if filename:
        img.save(filename)

    return img


def generate_witch_broom_image(
    width: int = 256, height: int = 256, filename: Optional[str] = None
) -> Image.Image:
    """Generate an artificial image showing witch broom disease symptoms."""
    img = Image.new("RGB", (width, height), color=(180, 200, 160))  # Grayish-green
    draw = ImageDraw.Draw(img)

    # Draw tree trunk (brown)
    trunk_x = width // 2
    trunk_y = height // 2
    draw.rectangle(
        [trunk_x - 5, trunk_y + 40, trunk_x + 5, trunk_y + 100],
        fill=(101, 67, 33),
    )

    # Draw abnormal dense branch growth (witch broom characteristic)
    abnormal_color = (100, 120, 80)  # Dark, unhealthy green
    for angle in range(0, 360, 20):
        import math

        rad = math.radians(angle)
        x_end = trunk_x + int(40 * math.cos(rad))
        y_end = trunk_y + int(40 * math.sin(rad))
        draw.line([trunk_x, trunk_y, x_end, y_end], fill=abnormal_color, width=2)

    # Draw dense foliage clumps
    for _ in range(6):
        x = random.randint(trunk_x - 50, trunk_x + 50)
        y = random.randint(trunk_y - 60, trunk_y + 10)
        r = random.randint(20, 35)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=abnormal_color)

    # Few or distorted lemons
    lemon_color = (200, 150, 0)  # Duller yellow
    for _ in range(2):
        x = random.randint(trunk_x - 40, trunk_x + 40)
        y = random.randint(trunk_y - 50, trunk_y + 10)
        draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=lemon_color)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    if filename:
        img.save(filename)

    return img


def generate_mango_trees_image(
    width: int = 256, height: int = 256, filename: Optional[str] = None
) -> Image.Image:
    """Generate an artificial image of mango trees (not lemon - should be Unknown)."""
    img = Image.new("RGB", (width, height), color=(220, 200, 150))  # Warm background
    draw = ImageDraw.Draw(img)

    # Tall dark foliage typical of mango trees
    mango_green = (46, 125, 50)  # Darker green than lemon
    for _ in range(10):
        x = random.randint(50, width - 50)
        y = random.randint(20, height - 40)
        r = random.randint(35, 55)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=mango_green)

    # Draw trunks
    for x in [100, 200]:
        draw.rectangle([x - 8, 150, x + 8, 250], fill=(139, 90, 43))

    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    if filename:
        img.save(filename)

    return img


def generate_blurred_image(
    width: int = 256, height: int = 256, filename: Optional[str] = None
) -> Image.Image:
    """Generate a blurred image (should be classified as Unknown)."""
    # Start with a normal healthy-looking image
    img = Image.new("RGB", (width, height), color=(200, 220, 180))
    draw = ImageDraw.Draw(img)

    # Add some shapes
    for _ in range(10):
        x = random.randint(0, width)
        y = random.randint(0, height)
        size = random.randint(20, 60)
        color = (random.randint(50, 150), random.randint(100, 200), random.randint(50, 150))
        draw.ellipse([x - size, y - size, x + size, y + size], fill=color)

    # Apply heavy blur to make it indistinguishable
    img = img.filter(ImageFilter.GaussianBlur(radius=8))

    if filename:
        img.save(filename)

    return img


def generate_sky_image(
    width: int = 256, height: int = 256, filename: Optional[str] = None
) -> Image.Image:
    """Generate an image of cloudy sky without trees."""
    img = Image.new("RGB", (width, height), color=(200, 220, 240))  # Light blue
    draw = ImageDraw.Draw(img)

    # Add some cloud-like shapes
    for _ in range(5):
        x = random.randint(0, width)
        y = random.randint(0, height - 100)
        draw.ellipse([x - 30, y - 15, x + 30, y + 15], fill=(220, 230, 250))

    img = img.filter(ImageFilter.GaussianBlur(radius=2))

    if filename:
        img.save(filename)

    return img


def create_test_images(output_dir: Path) -> dict[str, str]:
    """
    Create all artificial test images.
    Returns mapping of test case ID to image file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    images = {}

    # TC-1: Healthy lemon micro shoot
    tc1_path = output_dir / "TC-1_healthy_micro_shoot.png"
    generate_healthy_lemon_image(filename=str(tc1_path))
    images["TC-1"] = str(tc1_path)

    # TC-2: Witch broom lemon tree
    tc2_path = output_dir / "TC-2_witch_broom_tree.png"
    generate_witch_broom_image(filename=str(tc2_path))
    images["TC-2"] = str(tc2_path)

    # TC-3: Mango trees (not lemon)
    tc3_path = output_dir / "TC-3_mango_trees.png"
    generate_mango_trees_image(filename=str(tc3_path))
    images["TC-3"] = str(tc3_path)

    # TC-6: Sky without trees
    tc6_path = output_dir / "TC-6_cloudy_sky.png"
    generate_sky_image(filename=str(tc6_path))
    images["TC-6"] = str(tc6_path)

    # TC-8: Blurred micro shot
    tc8_path = output_dir / "TC-8_blurred_lemon.png"
    generate_blurred_image(filename=str(tc8_path))
    images["TC-8"] = str(tc8_path)

    return images


if __name__ == "__main__":
    from pathlib import Path

    test_images_dir = Path(__file__).parent / "test_data" / "vision_images"
    created = create_test_images(test_images_dir)
    print(f"Created {len(created)} test images:")
    for tc_id, path in created.items():
        print(f"  {tc_id}: {path}")

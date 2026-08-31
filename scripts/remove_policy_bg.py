import sys
from PIL import Image

def remove_policy_bg(image_path, out_path):
    try:
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"Error opening {image_path}: {e}")
        return

    width, height = img.size
    pixels = img.load()

    # Since it's a JPG, the white background might have compression artifacts 
    # (e.g. not exactly 255,255,255 but maybe 245,250,248).
    # We remove anything that is light enough to be background.
    for x in range(width):
        for y in range(height):
            r, g, b, a = pixels[x, y]
            if r > 220 and g > 220 and b > 220:
                pixels[x, y] = (255, 255, 255, 0)

    img.save(out_path, "PNG")
    print(f"Successfully removed background from {image_path} and saved as {out_path}!")

if __name__ == "__main__":
    remove_policy_bg("frontend/public/policy.jpg", "frontend/public/policy.png")

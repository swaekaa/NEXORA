import sys
from PIL import Image

def remove_watermarked_bg(image_path):
    try:
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"Error opening {image_path}: {e}")
        return

    width, height = img.size
    pixels = img.load()

    for x in range(width):
        for y in range(height):
            r, g, b, a = pixels[x, y]
            # Remove white and light-grey (the Adobe watermarks)
            # Doge is yellow/orange, so its Blue channel is low.
            # If all channels are high (R>210, G>210, B>210), it's background/watermark!
            if r > 210 and g > 210 and b > 210:
                pixels[x, y] = (255, 255, 255, 0)

    img.save(image_path, "PNG")
    print(f"Successfully removed watermarked background from {image_path}!")

if __name__ == "__main__":
    remove_watermarked_bg("frontend/public/buyer.png")

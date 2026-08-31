import sys
from PIL import Image

def remove_background(image_path):
    try:
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"Error opening {image_path}: {e}")
        return

    # Create a mask using flood fill from the top-left corner
    # to find all contiguous white pixels.
    width, height = img.size
    pixels = img.load()

    # The background color we want to remove (assume top-left pixel is background)
    bg_color = pixels[0, 0]
    
    # Simple threshold to check if pixel is "white-ish" background
    def is_bg(c):
        return c[0] > 240 and c[1] > 240 and c[2] > 240

    if not is_bg(bg_color):
        print(f"Top left pixel of {image_path} is not white. Skipping.")
        return

    # BFS to find all connected background pixels
    visited = set()
    queue = [(0, 0)]
    
    while queue:
        x, y = queue.pop(0)
        if (x, y) in visited:
            continue
        
        visited.add((x, y))
        
        # If it's a background pixel, make it transparent
        if is_bg(pixels[x, y]):
            pixels[x, y] = (255, 255, 255, 0)
            
            # Add neighbors
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) not in visited:
                        queue.append((nx, ny))

    img.save(image_path, "PNG")
    print(f"Successfully removed white background from {image_path}!")

if __name__ == "__main__":
    remove_background("frontend/public/buyer.png")
    remove_background("frontend/public/merchant.png")

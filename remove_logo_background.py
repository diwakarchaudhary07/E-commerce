#!/usr/bin/env python
"""
Script to remove background from logo3.png and make it transparent
"""
from PIL import Image
import os

def remove_background(image_path):
    """
    Remove white/light background from image and make it transparent
    """
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Get image data
        data = img.getdata()
        
        # Create new image data with transparent background
        new_data = []
        for item in data:
            # If pixel is white or very light (R>240, G>240, B>240), make it transparent
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))  # Transparent
            else:
                new_data.append(item)
        
        # Update image data
        img.putdata(new_data)
        
        # Save the image
        img.save(image_path, 'PNG')
        print(f"✓ Background removed successfully from {image_path}")
        print(f"✓ Image saved as PNG with transparent background")
        
    except Exception as e:
        print(f"✗ Error processing image: {e}")

if __name__ == "__main__":
    logo_path = os.path.join(
        os.path.dirname(__file__),
        "e_commerce",
        "static",
        "assets",
        "logo3.png"
    )
    
    if os.path.exists(logo_path):
        print(f"Processing: {logo_path}")
        remove_background(logo_path)
    else:
        print(f"✗ File not found: {logo_path}")

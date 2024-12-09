import base64
import hashlib
import os

import numpy as np
from PIL import Image

"""
This script is used to generate thermal images from thermal data strings. Just paste your sting into `thermal_data` and run the script.
"""

THERMAL_DATA = "FBMSExMTExMUExMTFBMTEhMTExISExMSExISExMTExMUExMSExQUFBQSEhMTHBkTFBMTExMUFBQSEhITFBMTEw=="
THERMAL_HASH = hashlib.md5(THERMAL_DATA.encode()).hexdigest()[:6]  # create a short hash to tack onto the filename

# code from the sandbox
encoded_thermal_data = THERMAL_DATA.encode()  # encode the thermal data to UTF-8
decoded_thermal_data = base64.b64decode(encoded_thermal_data)  # decode the thermal data from base 64
thermal_pixel_vals = list(bytearray(decoded_thermal_data))
thermal_array = np.array(thermal_pixel_vals).reshape(8, 8).T
thermal_grid = thermal_array.tolist()

# Print the thermal grid
print("\n".join([" ".join(map(str, row)) for row in thermal_grid]), end="\n\n")

# Normalize the pixel values to the range 0-255
min_temp = min(thermal_pixel_vals)
max_temp = max(thermal_pixel_vals)
normalized_pixels = [(int((p - min_temp) / (max_temp - min_temp) * 255)) for p in thermal_pixel_vals]

# Map normalized values to colored pixels
img = Image.new("RGB", (8, 8))
for i in range(8):
    for j in range(8):
        value = normalized_pixels[i * 8 + j]
        # Create a gradient from blue (cold) to red (hot)
        color = (value, 0, 255 - value)
        img.putpixel((i, j), color)

# Resize the image to 512x512
img = img.resize((512, 512), Image.NEAREST)  # type: ignore

# Create the directory if it doesn't exist
output_dir = os.path.join(os.path.dirname(__file__), "thermal_images")
os.makedirs(output_dir, exist_ok=True)
img_filename = f"ther_img_{THERMAL_HASH}.png"

# Save the image as the specified file
img.save(os.path.join(output_dir, img_filename))
print(f"Thermal image saved as {img_filename}")

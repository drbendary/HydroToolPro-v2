# mri_analysis.py

import cv2
import numpy as np


def analyze_mri_image(image_path):
    """
    Analyze the MRI image and return simulated values.
    In future: replace this logic with real image processing.

    Returns:
        dict: evans_index, callosal_angle, desh_presence
    """
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return {"error": "Unable to load image"}

        # Placeholder simulated values
        evans_index = round(np.random.uniform(0.3, 0.4), 2)
        callosal_angle = round(np.random.uniform(75, 100), 1)
        desh_detected = np.random.choice(["Yes", "No"])

        return {
            "evans_index": evans_index,
            "callosal_angle": callosal_angle,
            "desh_detected": desh_detected
        }

    except Exception as e:
        return {"error": str(e)}

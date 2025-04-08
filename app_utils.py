# app_utils.py

import os
import pydicom
import numpy as np


def calculate_evans_index(dicom_dir):
    """
    Reads the first DICOM file in the folder and calculates a mock Evans Index
    based on image dimensions. Replace with real measurements later.
    """
    for root, _, files in os.walk(dicom_dir):
        for file in files:
            if file.lower().endswith('.dcm'):
                dicom_path = os.path.join(root, file)
                ds = pydicom.dcmread(dicom_path)
                pixel_array = ds.pixel_array

                width = pixel_array.shape[1]
                bfr = int(width * 0.36)  # Frontal horn width (example)
                bifr = int(width * 1.2)  # Inner skull diameter (example)

                evans_index = round(bfr / bifr, 2)
                return evans_index
    return None

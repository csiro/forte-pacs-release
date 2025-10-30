"""
This module contains utilities for converting DICOM data to NumPy arrays.

This module provides functions for converting DICOM pixel data from raw bytes
to properly shaped and typed NumPy arrays, handling various DICOM pixel formats
including different bit depths, planar configurations, and sample arrangements.
"""
from typing import List, Any

import numpy
import numpy.typing as npt
from app.schema.dicom_pixel_data import DCMPixelData

def inst_frames_to_arrays(inst:DCMPixelData) -> List[npt.NDArray]:
    """
        Convert DICOM instance frames to NumPy arrays.

        Takes a DICOM instance and converts all its frames from raw bytes
        to properly shaped NumPy arrays using the instance's metadata.

        Args:
            inst (DCMInstance): DICOM instance containing frames and metadata.

        Returns:
            List[npt.NDArray]: List of NumPy arrays, one for each frame.
    """

    frames = []
    for frame in inst.frames:

        frames.append(buffer_to_array(frame, inst.rows, inst.columns, inst.bits_allocated,
                                     inst.samples_per_pixel, inst.pixel_representation,
                                     inst.planar_configuration))

    return frames

def buffer_to_array(buffer: bytes, rows: int, columns: int, bits_allocated: int,
                   samples_per_pixel: int, pixel_representation: int,
                   planar_configuration: int|None) -> npt.NDArray:
    """
        Convert raw pixel data buffer to a properly shaped NumPy array.

        Converts raw bytes to a NumPy array with appropriate data type and shape
        based on DICOM pixel data parameters. Handles different bit depths,
        signed/unsigned pixels, and planar configurations.

        Args:
            buffer (bytes): Raw pixel data bytes.
            rows (int): Number of rows in the image.
            columns (int): Number of columns in the image.
            bits_allocated (int): Number of bits allocated per pixel (8, 16, or 32).
            samples_per_pixel (int): Number of samples per pixel (1 for grayscale, 3 for RGB).
            pixel_representation (int): 0 for unsigned, 1 for signed pixels.
            planar_configuration (int): 0 for interleaved RGB, 1 for planar RGB.

        Returns:
            npt.NDArray: NumPy array with shape (rows, columns) for grayscale or
                        (rows, columns, samples_per_pixel) for color images.
    """

    np_dtype : Any  = numpy.uint8  # avoid warnings on mypy
    if bits_allocated == 16:
        if pixel_representation == 1:
            np_dtype = numpy.int16
        else:
            np_dtype = numpy.uint16
    elif bits_allocated == 32:
        if pixel_representation == 1:
            np_dtype = numpy.int32
        else:
            np_dtype = numpy.uint32
        np_dtype = numpy.uint32
    else:
        if pixel_representation == 1:
            np_dtype = numpy.int8
        else:
            np_dtype = numpy.uint8

    nparr = numpy.frombuffer(buffer, dtype=np_dtype)
    if samples_per_pixel == 1:
        return nparr.reshape(rows, columns)
    else:
        if planar_configuration == 0:
            return  nparr.reshape(rows, columns, samples_per_pixel)
        else:
            temp = nparr.reshape(samples_per_pixel,rows, columns)
            return temp.transpose(1,2,0)

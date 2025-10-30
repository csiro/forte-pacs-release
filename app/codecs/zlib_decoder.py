"""
This module contains a zlib-based decoder for deflated image frame compression.

"""
from typing import  Any, List, Tuple, cast
import zlib
import numpy.typing as npt
import pydicom
from app.codecs.decoder import Decoder, permute_rgb_to_requested_planar_config
from app.utils.numpy_utils import buffer_to_array

DeflatedImageFrameCompression = pydicom.uid.UID("1.2.840.10008.1.2.8.1")

def preflight()->Tuple[bool,str]:
    """
        Check if the decoder can be used.

        This function performs a preflight check for the zlib decoder. Since zlib is part
        of the Python standard library, it should always be available.

        Returns:
            tuple: A tuple containing (success_bool, error_message) where success_bool
                   is True if the decoder is available, and error_message is an empty
                   string on success or an error description on failure.
    """
    return (True,"")

class zlibDecoder(Decoder):
    """
        Zlib-based decoder for deflated image frame compression.

        This decoder uses the Python standard library zlib module to decompress
        deflated image frames, which use the DEFLATE compression algorithm.

        Supported transfer syntaxes:
            1.2.840.10008.1.2.1.99 - Deflated Explicit VR Little Endian

        Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

    """

    def __init__(self)->None:
        """
            Initialize the zlib decoder.

            Sets up the list of decodable media types, including deflated image frame
            compression and deflate application types.
        """
        self._decodable_mediatypes=[DeflatedImageFrameCompression,"application/x-deflate"]



    def decodable_mediatypes(self)->List[str]:
        """
            Get the list of media types that this decoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this decoder can decode.
        """
        return self._decodable_mediatypes

    def decode_image(self, pixel_data : bytes,  **kwargs: Any) -> npt.NDArray:
        """
            Decode a single image frame from pixel data using zlib decompression.

            This method uses the Python standard library zlib module to decompress
            deflated image data and converts it to a numpy array. For RGB images, it handles
            planar configuration transformations as needed.

            Args:
                pixel_data (bytes): Raw pixel data bytes to be decoded.
                **kwargs (Any): Additional decoding parameters including:
                    - columns (int): Width of the image in pixels
                    - rows (int): Height of the image in pixels
                    - bits_allocated (int): Number of bits allocated for pixel values
                    - samples_per_pixel (int): Number of samples per pixel
                    - pixel_representation (int): Pixel representation (signed/unsigned)
                    - planar_configuration (int): Current planar configuration
                    - requested_planar_configuration (int): Desired planar configuration for RGB images

            Returns:
                numpy.ndarray: Decoded image data as a numpy array.
        """

        frame_bytes = zlib.decompress(pixel_data, wbits=-zlib.MAX_WBITS)

        columns = cast(int,kwargs.get("columns"))
        rows = cast(int,kwargs.get("rows"))
        bits_allocated = cast(int,kwargs.get("bits_allocated"))
        samples_per_pixel = cast(int,kwargs.get("samples_per_pixel"))
        pixel_representation = cast(int,kwargs.get("pixel_representation"))
        planar_configuration = cast(int,kwargs.get("planar_configuration"))
        requested_planar_configuration = int(kwargs.get("requested_planar_configuration",0))

        temp = buffer_to_array(frame_bytes,rows,columns,bits_allocated,samples_per_pixel,\
            pixel_representation,planar_configuration)

        if samples_per_pixel == 3:
            temp = permute_rgb_to_requested_planar_config(temp,requested_planar_configuration)

        return temp

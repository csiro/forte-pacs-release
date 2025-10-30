"""
This module contains a Pillow-based decoder for various image formats.

"""
from typing import  Any, Tuple, List
import io
import numpy
import numpy.typing as npt
import pydicom
from app.codecs.decoder import Decoder,permute_rgb_to_requested_planar_config
from PIL import Image

JPEGXLLossless = pydicom.uid.UID("1.2.840.10008.1.2.4.110")
JPEGXLJPEGRecompression = pydicom.uid.UID("1.2.840.10008.1.2.4.111")
JPEGXL = pydicom.uid.UID("1.2.840.10008.1.2.4.112")

def preflight()->Tuple[bool,str]:
    """
        Check if the decoder can be used.

        This function performs a preflight check to determine if the Pillow decoder
        is available and can be used for decoding operations.

        Returns:
            tuple: A tuple containing (success_bool, error_message) where success_bool
                   is True if the decoder is available, and error_message is an empty
                   string on success or an error description on failure.
    """
    return (True,"")

class pillowDecoder(Decoder):
    """
        Pillow-based decoder for various image formats.

        This decoder uses the Python Pillow library to decode various image formats
        including PNG, GIF, and optionally JPEG XL if the pillow_jxl extension is available.

        Supported transfer syntaxes:
            1.2.840.10008.1.2.4.50
            1.2.840.10008.1.2.4.51
            1.2.840.10008.1.2.4.57
            1.2.840.10008.1.2.4.70

        Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

    """

    def __init__(self)->None:
        """
            Initialize the Pillow decoder.

            Sets up the list of decodable media types, including PNG and GIF by default.
            If the pillow_jxl extension is available, also adds JPEG XL support.
        """
        self._decodable_mediatypes=["image/png",
                "image/gif"]
        


    def decodable_mediatypes(self)->List[str]:
        """
            Get the list of media types that this decoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this decoder can decode.
        """
        return self._decodable_mediatypes


    def decode_image(self, pixel_data : bytes,    **kwargs: Any) -> npt.NDArray:
        """
            Decode a single image frame from pixel data using Pillow.

            This method uses the Pillow library to decode image data from various formats
            and returns the decoded pixel data as a numpy array. For RGB images, it handles
            planar configuration transformations as needed.

            Args:
                pixel_data (bytes): Raw pixel data bytes to be decoded.
                **kwargs (Any): Additional decoding parameters including:
                    - requested_planar_configuration (int): Desired planar configuration for RGB images

            Returns:
                numpy.ndarray: Decoded image data as a numpy array.
        """

        requested_planar_configuration = kwargs.get("requested_planar_configuration",0)
        #samples_per_pixel = kwargs.get("samples_per_pixel")

        stream = io.BytesIO(pixel_data)

        temp = numpy.array(Image.open(stream))

        if len(temp.shape) == 3:
            temp = permute_rgb_to_requested_planar_config(temp,requested_planar_configuration)
        return temp

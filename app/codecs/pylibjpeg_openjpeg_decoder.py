"""
This module contains a pylibjpeg-based decoder for JPEG 2000 and HTJ2K image formats.

"""
from typing import  Any, Tuple, List
import numpy.typing as npt
from pydicom.uid import JPEG2000Lossless,  JPEG2000, HTJ2KLossless, HTJ2KLosslessRPCL, HTJ2K
from app.codecs.decoder import Decoder,permute_rgb_to_requested_planar_config

HAS_OPENJPEG = False

try:
    from openjpeg import decode
    HAS_OPENJPEG = True
except ImportError:
    pass


def preflight()->Tuple[bool,str]:
    """
        Check if the decoder can be used.

        This function performs a preflight check to determine if the OpenJPEG library
        is available and can be used for decoding JPEG 2000 operations.

        Returns:
            tuple: A tuple containing (success_bool, error_message) where success_bool
                   is True if the decoder is available, and error_message is an empty
                   string on success or an error description on failure.
    """
    if not HAS_OPENJPEG:
        return (False,"openjpeg not installed")
    return (True,"")

class pylibOpenJpegDecoder(Decoder):
    """
        PyLibJPEG OpenJPEG-based decoder for JPEG 2000 and HTJ2K image formats.

        This decoder uses the pylibjpeg library with OpenJPEG backend to decode
        JPEG 2000 and HTJ2K (High Throughput JPEG 2000) image formats.

        Supported transfer syntaxes:
            1.2.840.10008.1.2.4.201 - JPEG 2000 Lossless
            1.2.840.10008.1.2.4.202 - JPEG 2000 Lossy
            1.2.840.10008.1.2.4.203 - HTJ2K Lossless and Lossy

        Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

    """

    def __init__(self) -> None:
        """
            Initialize the PyLibJPEG OpenJPEG decoder.

            Sets up the list of decodable media types, including JPEG 2000 and HTJ2K formats
            supported by the OpenJPEG library.
        """
        self._decodable_mediatypes=[JPEG2000Lossless,
                JPEG2000,
                HTJ2KLossless,
                HTJ2KLosslessRPCL,
                HTJ2K,
                "image/jp2",
                "image/jphc"]


    def decodable_mediatypes(self) -> List[str]:
        """
            Get the list of media types that this decoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this decoder can decode.
        """
        return self._decodable_mediatypes


    def decode_image(self,pixel_data : bytes,     **kwargs: Any) -> npt.NDArray:
        """
            Decode a single image frame from pixel data using OpenJPEG.

            This method uses the pylibjpeg library with OpenJPEG backend to decode
            JPEG 2000 and HTJ2K image data and returns the decoded pixel data as a numpy array.
            For RGB images, it handles planar configuration transformations as needed.

            Args:
                pixel_data (bytes): Raw pixel data bytes to be decoded.
                **kwargs (Any): Additional decoding parameters including:
                    - requested_planar_configuration (int): Desired planar configuration for RGB images

            Returns:
                numpy.ndarray: Decoded image data as a numpy array.
        """
        requested_planar_configuration = kwargs.get("requested_planar_configuration",0)
        #samples_per_pixel = kwargs.get("samples_per_pixel")
        temp =  decode(pixel_data)
        if len(temp.shape) == 3:
            temp = permute_rgb_to_requested_planar_config(temp,requested_planar_configuration)
        return temp

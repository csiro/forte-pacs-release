"""
This module contains a PyTurboJPEG-based decoder for JPEG and JPEG-LS image formats.

"""
from typing import Any, List, Tuple
import logging
import numpy.typing as npt
from pydicom.uid import JPEGBaseline8Bit, JPEGExtended12Bit, \
    JPEGLossless, JPEGLosslessSV1
from app.codecs.decoder import Decoder,permute_rgb_to_requested_planar_config
from app.codecs.codec_utils import get_param



HAS_TURBOJPEG = False
try:
    from app.extern.PyTurboJpeg3 import TurboJPEG3, TJPF_GRAY, TJPF_RGB
    HAS_TURBOJPEG = True
except ImportError as e:
    logging.info(str(e))
    logging.debug(str(e))
    pass

from ctypes import *
from ctypes.util import find_library

def preflight()->Tuple[bool,str]:
    """
        Check if the decoder can be used.

        This function performs a preflight check to determine if the libjpeg library
        is available and can be used for decoding JPEG operations.

        Returns:
            tuple: A tuple containing (success_bool, error_message) where success_bool
                   is True if the decoder is available, and error_message is an empty
                   string on success or an error description on failure.
    """
    logging.info("TurboJPEG %s"%HAS_TURBOJPEG)
    if not HAS_TURBOJPEG:
        return (False,"PYTurboJPeg not installed")
    return (True,"")

logger = logging.getLogger(__name__)


class turboJpegDecoder(Decoder):
    """

        PyTurboJPEG-based decoder for JPEG and JPEG-LS image formats.

        This decoder uses the PyTurboJPEG library to decode various JPEG formats
        including baseline JPEG, extended JPEG, lossless JPEG, and JPEG-LS.

        Supported transfer syntaxes:
            1.2.840.10008.1.2.4.50 - JPEG Baseline 8-bit
            1.2.840.10008.1.2.4.51 - JPEG Extended 12-bit
            1.2.840.10008.1.2.4.57 - JPEG Lossless
            1.2.840.10008.1.2.4.70 - JPEG Lossless SV1


        Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

    """

    def __init__(self) -> None:
        """
            Initialize the PyTurboJPEG decoder.

            Sets up the list of decodable media types, including various JPEG formats
            and JPEG-LS formats supported by the libjpeg library.
        """
        self._decodable_mediatypes=[JPEGBaseline8Bit,
                JPEGExtended12Bit,
                JPEGLossless,
                JPEGLosslessSV1,

                "image/jpeg"]


    def decodable_mediatypes(self) -> List[str]:
        """
            Get the list of media types that this decoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this decoder can decode.
        """
        return self._decodable_mediatypes

    def decode_image(self, pixel_data : bytes,     **kwargs: Any) -> npt.NDArray:
        """
            Decode a single image frame from pixel data using PyTurboJPEG.

            This method uses the PyTurboJPEG library to decode JPEG and JPEG-LS image data
            and returns the decoded pixel data as a numpy array. For RGB images, it handles
            planar configuration transformations as needed.

            Args:
                pixel_data (bytes): Raw pixel data bytes to be decoded.
                **kwargs (Any): Additional decoding parameters including:
                    - requested_planar_configuration (int): Desired planar configuration for RGB images

            Returns:
                numpy.ndarray: Decoded image data as a numpy array.
        """
        logger.info ("Before decode 1 ")


        requested_planar_configuration = int(get_param(kwargs,"requested_planar_configuration"))
        samples_per_pixel = int(get_param(kwargs,"samples_per_pixel"))
        
        jpeg = TurboJPEG3('/opt/libjpeg-turbo/lib64/libturbojpeg.so')

        if samples_per_pixel == 1:
            temp = jpeg.decode(pixel_data,TJPF_GRAY)
        elif samples_per_pixel == 3:
            temp = jpeg.decode(pixel_data,TJPF_RGB)
            temp = permute_rgb_to_requested_planar_config(temp,requested_planar_configuration)


        logger.info ("after  decode")


        return temp

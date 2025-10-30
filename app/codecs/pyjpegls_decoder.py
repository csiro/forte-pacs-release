"""
This module contains a PyTurboJPEG-based decoder for JPEG and JPEG-LS image formats.

"""
from typing import Any, List, Tuple
import logging
import numpy
import numpy.typing as npt
from pydicom.uid import  JPEGLSLossless, JPEGLSNearLossless
from app.codecs.decoder import Decoder,permute_rgb_to_requested_planar_config
from app.codecs.codec_utils import get_param

HAS_PYJPEGLS = False
try:
    from jpeg_ls import decode_buffer
    HAS_PYJPEGLS = True
except ImportError as e:
    logging.info(str(e))
    logging.debug(str(e))


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
    if not HAS_PYJPEGLS:
        return (False,"PYJPEGLS not installed")
    return (True,"")

logger = logging.getLogger(__name__)


class pyJpegLSDecoder(Decoder):
    """

        PyJPEGLS-based decoder for  JPEG-LS image formats.

        This decoder uses the PYJPEGLS library to decode  JPEG-LS.

        Supported transfer syntaxes:

            1.2.840.10008.1.2.4.80 - JPEG-LS Lossless
            1.2.840.10008.1.2.4.81 - JPEG-LS Near Lossless

        Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

    """

    def __init__(self) -> None:
        """
            Initialize the PyTurboJPEG decoder.

            Sets up the list of decodable media types, including various JPEG formats
            and JPEG-LS formats supported by the libjpeg library.
        """
        self._decodable_mediatypes=[
                JPEGLSLossless,
                JPEGLSNearLossless,
                "image/jls"]


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

        requested_planar_configuration = int(get_param(kwargs,"requested_planar_configuration"))
        samples_per_pixel = int(get_param(kwargs,"samples_per_pixel"))
        bits_allocated = int(get_param(kwargs,"bits_allocated"))
        rows = int(get_param(kwargs,"rows"))
        columns = int(get_param(kwargs,"columns"))

        (output_bytes,_) = decode_buffer(pixel_data)

        dtype_ : npt.DTypeLike = numpy.uint8
        if bits_allocated == 16:
            dtype_ = numpy.uint16

        temp = numpy.frombuffer(output_bytes,dtype=dtype_)

        if samples_per_pixel == 3:
            temp = numpy.reshape(temp,(rows,columns,3))
            temp = permute_rgb_to_requested_planar_config(temp,requested_planar_configuration)
        else:
            temp = numpy.reshape(temp, (rows,columns))

        logger.info ("after  decode")


        return temp

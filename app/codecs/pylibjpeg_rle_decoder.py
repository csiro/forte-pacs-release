"""
This module contains a pylibjpeg-based decoder for RLE (Run Length Encoding) image compression.

"""
from typing import  Any, Tuple, Sequence
from pydicom.uid import RLELossless
import numpy.typing as npt
from app.codecs.decoder import Decoder,permute_rgb_to_requested_planar_config
from app.codecs.codec_utils import get_param

HAS_RLE = False
try:
    from rle import decode_pixel_data
    HAS_RLE = True
except ImportError:
    pass


def preflight() ->  Tuple[bool,str]:
    """
        Check if the decoder can be used.

        This function performs a preflight check to determine if the pylibjpeg-rle library
        is available and can be used for decoding RLE operations.

        Returns:
            tuple: A tuple containing (success_bool, error_message) where success_bool
                   is True if the decoder is available, and error_message is an empty
                   string on success or an error description on failure.
    """
    if not HAS_RLE:
        return (False,"pylibjpeg-rle not installed")
    return (True,"")

class pylibJpegRLEDecoder(Decoder):
    """
        PyLibJPEG RLE-based decoder for RLE (Run Length Encoding) image compression.

        This decoder uses the pylibjpeg-rle library to decode RLE compressed image data,
        which is a lossless compression method commonly used in DICOM images.

        Supported transfer syntaxes:
            1.2.840.10008.1.2.4.5 - RLE Lossless

        Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

    """

    def __init__(self) -> None:
        """
            Initialize the PyLibJPEG RLE decoder.

            Sets up the list of decodable media types, including RLE Lossless format
            supported by the pylibjpeg-rle library.
        """
        self._decodable_mediatypes=[RLELossless]


    def decodable_mediatypes(self) -> Sequence[str]:
        """
            Get the list of media types that this decoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this decoder can decode.
        """
        return self._decodable_mediatypes

    def decode_image(self, pixel_data : bytes, **kwargs: Any) -> npt.NDArray:
        """
            Decode a single image frame from pixel data using RLE decompression.

            This method uses the pylibjpeg-rle library to decode RLE compressed image data
            and returns the decoded pixel data as a numpy array. For RGB images, it handles
            planar configuration transformations as needed.

            Args:
                pixel_data (bytes): Raw pixel data bytes to be decoded.
                **kwargs (Any): Additional decoding parameters including:
                    - requested_planar_configuration (int): Desired planar configuration for RGB images
                    - samples_per_pixel (int): Number of samples per pixel

            Returns:
                numpy.ndarray: Decoded image data as a numpy array.
        """
        
        requested_planar_configuration = int(get_param(kwargs,"requested_planar_configuration"))
        samples_per_pixel = int(get_param(kwargs,"samples_per_pixel"))
        bits_allocated = int(get_param(kwargs,"bits_allocated"))
        rows = int(get_param(kwargs,"rows"))
        columns = int(get_param(kwargs,"columns"))

        params = {"rows":rows,"columns":columns,"bits_alllocated":bits_allocated}
        temp =  decode_pixel_data(pixel_data, None, version=1, ** params)
        # we can ignore the types below because the output is expected to be a numpy array
        # as we ahve specified version 1 of the algorithm
        # ideally we should cast
        if samples_per_pixel == 3:
            temp = permute_rgb_to_requested_planar_config(temp,requested_planar_configuration) # type: ignore
        return temp # type: ignore

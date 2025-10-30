"""
This module contains a pylibjpeg-based encoder for RLE (Run Length Encoding) image compression.

"""
from typing import  Any, Sequence, Tuple
import logging
import math
from pydicom.uid import JPEGLSLossless, JPEGLSNearLossless
from app.codecs.encoder import Encoder
from app.schema.dicom_instance import DCMPixelData
from app.codecs.codec_utils import get_param

HAS_PYJPEGLS = False
try:
    from jpeg_ls import encode_buffer
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

class pyJpegLSEncoder(Encoder):
    """
        PyLibJPEG RLE-based encoder for RLE (Run Length Encoding) image compression.

        This encoder uses the pylibjpeg-rle library to encode images using RLE compression,
        which is a lossless compression method commonly used in DICOM images.

        Supported transfer syntaxes:
            1.2.840.10008.1.2.4.5 - RLE Lossless

        Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

    """

    def __init__(self) -> None:
        """
            Initialize the PyLibJPEG RLE encoder.

            Sets up the list of encodable media types, including RLE Lossless format
            supported by the pylibjpeg-rle library.
        """
        self._encodable_mediatypes=[
                JPEGLSLossless,
                JPEGLSNearLossless,
                "image/jls"]


    def encodable_mediatypes(self) -> Sequence[str]:
        """
            Get the list of media types that this encoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this encoder can encode.
        """
        return self._encodable_mediatypes

    def encode_inst(self,inst : DCMPixelData, transfer_syntax :str) -> DCMPixelData:
        """
            Encode a DICOM instance's pixel data using the specified transfer syntax.

            This method processes the pixel data of a DICOM instance, encoding each frame
            using RLE compression and returns a new DCMPixelData object. RLE is a lossless
            compression method that preserves the original photometric interpretation.

            Args:
                inst (DCMPixelData): The DICOM pixel data to encode.
                transfer_syntax (str): The transfer syntax to use for encoding (RLE Lossless).

            Returns:
                DCMPixelData: Encoded pixel data as a DCMPixelData object with updated
                             transfer syntax.
        """


        frames = []

        params = {}
        params["bits_allocated"] = inst.bits_allocated
        params["columns"] = inst.columns
        params["rows"] = inst.rows
        params["samples_per_pixel"] = inst.samples_per_pixel

        for frame in inst.frames:

            encoded_frame = self.encode_image(frame,transfer_syntax,**params)

            frames.append(encoded_frame)

        photo_interpretation = inst.photometric_interpretation


        pd = DCMPixelData(
            number_of_frames=inst.number_of_frames,
            transfer_syntax_uid=transfer_syntax,
            pixel_data_format="INT",
            samples_per_pixel=inst.samples_per_pixel,
            photometric_interpretation=photo_interpretation,
            rows=inst.rows,
            columns=inst.columns,
            bits_allocated=inst.bits_allocated,
            bits_stored=inst.bits_stored,
            high_bit=inst.high_bit,
            planar_configuration=0, # always zero
            frames=frames,
            smallest_image_pixel_value=inst.smallest_image_pixel_value,
            largest_image_pixel_value=inst.largest_image_pixel_value,
            pixel_representation=inst.pixel_representation
        )  ## if we are doing decode, then we are not looking at palette color
        return pd

    def encode_image(self,data: bytes,transfer_syntax: str, **kwargs: Any) -> bytes:
        """
            Encode a single image frame from pixel data using RLE compression.

            This method uses the pylibjpeg-rle library to encode image data using
            RLE (Run Length Encoding) compression, which is a lossless compression method.

            Args:
                data (bytes): Raw pixel data bytes to be encoded.
                transfer_syntax (str): The transfer syntax to use for encoding (RLE Lossless).
                **kwargs (Any): Additional encoding parameters including:
                    - bits_allocated (int): Number of bits allocated for pixel values
                    - columns (int): Width of the image in pixels
                    - rows (int): Height of the image in pixels
                    - samples_per_pixel (int): Number of samples per pixel

            Returns:
                bytes: Encoded image data as bytes.

            Raises:
                Exception: If the transfer syntax is not supported.
        """

        if transfer_syntax not in self._encodable_mediatypes:
            raise Exception("Transfer Syntax not supported")


        samples_per_pixel = int(get_param(kwargs,"samples_per_pixel"))
        bits_stored = int(get_param(kwargs,"bits_stored"))
        rows = int(get_param(kwargs,"rows"))
        columns = int(get_param(kwargs,"columns"))
        lossy_error = 0

        if transfer_syntax == JPEGLSNearLossless:
            lossy_error = int (math.pow(2,bits_stored)*0.05) ## allow max 5% deviation

        return encode_buffer(data, rows,columns,samples_per_pixel,bits_stored,lossy_error,interleave_mode=0)

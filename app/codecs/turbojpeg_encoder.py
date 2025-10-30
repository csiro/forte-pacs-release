"""
This module contains a pylibjpeg-based encoder for RLE (Run Length Encoding) image compression.

"""
from typing import  Any, Sequence, Tuple, Dict
from pydicom.uid import JPEGBaseline8Bit, JPEGExtended12Bit, \
    JPEGLossless, JPEGLosslessSV1
from app.codecs.encoder import Encoder
from app.schema.dicom_instance import DCMPixelData
from app.codecs.codec_utils import get_param

HAS_TURBOJPEG = False
try:
    from app.extern.PyTurboJpeg3 import TurboJPEG3, TJPF_GRAY, TJPF_RGB
    HAS_TURBOJPEG = True
except ImportError:
    pass


def preflight() -> Tuple[bool, str]:
    """
        Check if the encoder can be used.

        This function performs a preflight check to determine if the pylibjpeg-rle library
        is available and can be used for encoding RLE operations.

        Returns:
            tuple: A tuple containing (success_bool, error_message) where success_bool
                   is True if the encoder is available, and error_message is an empty
                   string on success or an error description on failure.
    """
    if not HAS_TURBOJPEG:
        return (False,"TurboJPEG not installed")
    return (True,"")

class turboJpegDecoder (Encoder):
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
        self._encodable_mediatypes=[JPEGBaseline8Bit,
                JPEGExtended12Bit,
                JPEGLossless,
                JPEGLosslessSV1,

                "image/jpeg"]


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


    def ts2params(self,transfer_syntax: str) -> Dict[str,Any]:
        """
            Return the compression parameters for teh codec based on transfer syntax
        """
        params = {}
        if transfer_syntax in [JPEGLossless,JPEGLosslessSV1]:
            params["TJPARAM_LOSSLESS"] = 1
            params["TJPARAM_LOSSLESSPT"] = 0

            if transfer_syntax == JPEGLosslessSV1:
                params["TJPARAM_LOSSLESSPSV"] = 1
            else:
                params["TJPARAM_LOSSLESSPSV"] = 6

        else:
            params["TJPARAM_LOSSLESS"] = 0
            params["TJPARAM_QUALITY"] = 90
            params["TJPARAM_SUBSAMP"] = 1 # "TJSAMP_422"

        return params

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
    #    requested_planar_configuration = kwargs.get("requested_planar_configuration",0)

        samples_per_pixel = int(get_param(kwargs,"samples_per_pixel"))
        bits_stored = int(get_param(kwargs,"bits_stored"))
        bits_allocated = int(get_param(kwargs,"bits_allocated"))
        rows = int(get_param(kwargs,"rows"))
        columns = int(get_param(kwargs,"columns"))

        if transfer_syntax not in self._encodable_mediatypes:
            raise Exception("Transfer Syntax not supported")

        #1.2.840.10008.1.2.4.50 - JPEG Baseline 8-bit
        #1.2.840.10008.1.2.4.51 - JPEG Extended 12-bit
        #1.2.840.10008.1.2.4.57 - JPEG Lossless
        #1.2.840.10008.1.2.4.70 - JPEG Lossless SV1
        ## make a numpy array

        if transfer_syntax in [JPEGLossless,JPEGLosslessSV1]:
            if bits_stored > 16:
                raise Exception("Jpeg Lossless transfer syntax can only store a maximum of 16 bits per channel.")
        if transfer_syntax  == JPEGBaseline8Bit and bits_stored != 8:
            raise Exception("Jpeg Baseline transfer syntax can only store a maximum of 8 bits per channel")
        if transfer_syntax == JPEGExtended12Bit:
            if samples_per_pixel != 1:
                raise Exception("Jpeg Extented tranfer syntax can only store grayscale images")
            elif bits_stored not in [8,12]:
                raise Exception("Jpeg Extented tranfer syntax can only store 8 or 12 bits per channel")

        params = self.ts2params(transfer_syntax)

        pixel_format = TJPF_GRAY
        if samples_per_pixel == 3:
            pixel_format = TJPF_RGB
        jpeg = TurboJPEG3('/opt/libjpeg-turbo/lib64/libturbojpeg.so')

        output = jpeg.encode_bytes(data, columns, rows, samples_per_pixel, bits_allocated, pixel_format, **params)

        if output is not None:
            return output
        else:
            raise Exception("Error while eoncidng data")

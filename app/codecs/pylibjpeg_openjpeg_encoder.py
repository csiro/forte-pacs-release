"""
This module contains a pylibjpeg-based encoder for JPEG 2000 image formats.

"""
from typing import List, Any, cast, Tuple
from pydicom.uid import JPEG2000Lossless,  JPEG2000
from app.codecs.encoder import Encoder
from app.schema.dicom_instance import DCMPixelData
from app.codecs.codec_utils import get_param


HAS_OPENJPEG = False
try:
    from openjpeg.utils import encode_buffer
    HAS_OPENJPEG = True
except ImportError:
    pass


def preflight() ->  Tuple[bool, str]:
    """
        Check if the encoder can be used.
        
        This function performs a preflight check to determine if the OpenJPEG library
        is available and can be used for encoding JPEG 2000 operations.
        
        Returns:
            tuple: A tuple containing (success_bool, error_message) where success_bool
                   is True if the encoder is available, and error_message is an empty
                   string on success or an error description on failure.
    """
    if not HAS_OPENJPEG:
        return (False,"openjpeg not installed")
    return (True,"")

class pylibOpenJpegEncoder(Encoder):
    """
        PyLibJPEG OpenJPEG-based encoder for JPEG 2000 image formats.

        This encoder uses the pylibjpeg library with OpenJPEG backend to encode
        images into JPEG 2000 format, supporting both lossless and lossy compression.

        Supported transfer syntaxes:
            1.2.840.10008.1.2.4.201 - JPEG 2000 Lossless
            1.2.840.10008.1.2.4.202 - JPEG 2000 Lossy
            1.2.840.10008.1.2.4.203 - HTJ2K (when available)

        Reference: https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

    """

    def __init__(self) -> None:
        """
            Initialize the PyLibJPEG OpenJPEG encoder.
            
            Sets up the list of encodable media types, including JPEG 2000 formats
            supported by the OpenJPEG library.
        """
        self._encodable_mediatypes=[JPEG2000Lossless,
                JPEG2000,
                "image/jp2",
                "image/jphc"]


    def encodable_mediatypes(self) -> List[str]:
        """
            Get the list of media types that this encoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this encoder can encode.
        """
        return self._encodable_mediatypes

    def encode_inst(self,inst : DCMPixelData, transfer_syntax: str) -> DCMPixelData:
        """
            Encode a DICOM instance's pixel data using the specified transfer syntax.

            This method processes the pixel data of a DICOM instance, encoding each frame
            using the specified JPEG 2000 transfer syntax and returns a new DCMPixelData object.
            It handles photometric interpretation conversions for RGB images based on the
            compression type (YBR_ICT for lossy, YBR_RCT for lossless).

            Args:
                inst (DCMPixelData): The DICOM pixel data to encode.
                transfer_syntax (str): The transfer syntax to use for encoding.

            Returns:
                DCMPixelData: Encoded pixel data as a DCMPixelData object with updated
                             transfer syntax and photometric interpretation.
        """


        frames = []

        params : dict[str,Any] = {}
        params["photometric_interpretation"] = inst.photometric_interpretation
        params["bits_allocated"] = inst.bits_allocated
        params["bits_stored"] = inst.bits_stored
        params["columns"] = inst.columns
        params["rows"] = inst.rows
        params["samples_per_pixel"] = inst.samples_per_pixel
        params["is_signed"] = bool(inst.pixel_representation)

        for frame in inst.frames:

            encoded_frame = self.encode_image(frame,transfer_syntax,**params)

            frames.append(encoded_frame)

        photo_interpretation = inst.photometric_interpretation

        if inst.samples_per_pixel == 3 :
            if transfer_syntax == JPEG2000:
                photo_interpretation = "YBR_ICT"
            elif transfer_syntax == JPEG2000Lossless:
                photo_interpretation = "YBR_RCT"

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

    def encode_image(self,data:bytes,transfer_syntax:str, **kwargs: Any) -> bytes:
        """
            Encode a single image frame from pixel data using OpenJPEG.

            This method uses the pylibjpeg library with OpenJPEG backend to encode
            image data into JPEG 2000 format. It supports both lossless and lossy compression
            with configurable compression ratios.

            Args:
                data (bytes): Raw pixel data bytes to be encoded.
                transfer_syntax (str): The transfer syntax to use for encoding.
                **kwargs (Any): Additional encoding parameters including:
                    - photometric_interpretation (str): Color interpretation of the image
                    - bits_stored (int): Number of bits used to store pixel values
                    - columns (int): Width of the image in pixels
                    - rows (int): Height of the image in pixels
                    - samples_per_pixel (int): Number of samples per pixel
                    - is_signed (bool): Whether pixel values are signed

            Returns:
                bytes: Encoded image data as bytes.

            Raises:
                Exception: If the transfer syntax is not supported.
        """

        if transfer_syntax not in self._encodable_mediatypes:
            raise Exception("Transfer Syntax not supported") ## TODO exceptions

        compression_ratios : List[float]= []

        samples_per_pixel = int(get_param(kwargs,"samples_per_pixel"))
        bits_stored = int(get_param(kwargs,"bits_stored"))
        rows = int(get_param(kwargs,"rows"))
        columns = int(get_param(kwargs,"columns"))
        is_signed = bool(get_param(kwargs,"is_signed"))
        pi = get_param(kwargs,"photometric_interpretation")
        
        photometric_interpretation = 2
        if pi in ["MONOCHROME1","MONOCHROME2"]:
            photometric_interpretation = 2
        elif pi == "RGB":
            photometric_interpretation = 1


        if transfer_syntax  == JPEG2000Lossless:
            compression_ratios = []
        elif transfer_syntax == JPEG2000:
            compression_ratios= [5,2]

        return encode_buffer(data,columns, rows, samples_per_pixel, bits_stored, is_signed,
                             photometric_interpretation=photometric_interpretation,
                             #use_mct = use_mct,
                             compression_ratios=compression_ratios,
                             codec_format=0)

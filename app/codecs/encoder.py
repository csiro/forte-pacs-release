

"""
This module contains the encoder abstract base class and utils.

"""

from abc import ABC, abstractmethod
from typing import Sequence
from app.schema.dicom_pixel_data import DCMPixelData

class Encoder(ABC):
    """
        Abstract base class for encoding DICOM image data.

        This class provides an interface for encoding DICOM image instances,
        with methods to encode individual images and determine supported media types.

    """

    @abstractmethod
    def encode_image(self,data : bytes ,transfer_syntax : str) -> bytes:
        """
            Encode a single image frame from pixel data.

            This abstract method must be implemented by subclasses to encode a single image frame
            from raw pixel data bytes, using the specified transfer syntax.

            Args:
                data (bytes): Raw pixel data bytes to be encoded.
                transfer_syntax (str): The transfer syntax to use for encoding.

            Returns:
                bytes: Encoded image data as bytes.

            Raises:
                NotImplementedError: If the method is not implemented by a subclass.
        """

    @abstractmethod
    def encode_inst(self,inst : DCMPixelData,transfer_syntax : str) -> DCMPixelData:
        """
            Encode a DICOM instance's pixel data using the specified transfer syntax.

            This method processes the pixel data of a DICOM instance, encoding each frame
            using the specified transfer syntax and returns a new DCMPixelData object.

            Args:
                inst (DCMPixelData): The DICOM pixel data to encode.
                transfer_syntax (str): The transfer syntax to use for encoding.

            Returns:
                DCMPixelData: Encoded pixel data as a DCMPixelData object.

            Raises:
                NotImplementedError: If the method is not implemented by a subclass.
        """

    @abstractmethod
    def encodable_mediatypes(self)-> Sequence[str]:
        """
            Get the list of media types that this encoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this encoder can encode.
        """

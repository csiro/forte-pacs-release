"""
This module contains the decoder abstract base class and utils.

"""

from typing import Sequence, Any, Dict
from abc import ABC, abstractmethod
from pydicom.uid import ExplicitVRLittleEndian
import numpy.typing as npt
import numpy
from app.schema.dicom_pixel_data import DCMPixelData
from app.schema.dicom_instance import DCMInstance



def permute_rgb_to_requested_planar_config(pixel_data : npt.NDArray, requested_planar_config : int) -> npt.NDArray:
    """
        Permute RGB pixel data to the requested planar configuration.

        This function rearranges the dimensions of RGB pixel data based on the specified
        planar configuration. It supports converting between planar configurations 0 and 1
        for 3-channel images.

        Args:
            pixel_data (numpy.ndarray): Input pixel data array.
            requested_planar_config (int): Desired planar configuration (0 or 1).

        Returns:
            numpy.ndarray: Pixel data with rearranged dimensions matching the requested
            planar configuration.
    """
    if requested_planar_config == 0 and pixel_data.shape[2] == 3:
        return numpy.moveaxis(pixel_data,2,0)
    elif requested_planar_config == 1 and pixel_data.shape[0] == 3:
        return numpy.moveaxis(pixel_data,0,2)
    return pixel_data

class Decoder(ABC):
    """
        Abstract base class for decoding DICOM image data.

        This class provides an interface for decoding DICOM image instances,
        with methods to decode individual images and determine supported media types.

    """


    @abstractmethod
    def decode_image(self, pixel_data : bytes,    **kwargs: Any) -> npt.NDArray:
        """
            Decode a single image frame from pixel data.

            This abstract method must be implemented by subclasses to decode a single image frame
            from raw pixel data bytes, using the provided parameters.

            Args:
                pixel_data (bytes): Raw pixel data bytes to be decoded.
                **kwargs (Any): Additional decoding parameters such as image dimensions,
                                color interpretation, bit depth, etc.

            Returns:
                numpy.ndarray: Decoded image data as a numpy array.

            Raises:
                NotImplementedError: If the method is not implemented by a subclass.
        """


    @abstractmethod
    def decodable_mediatypes(self) -> Sequence[str]:
        """
            Get the list of media types that this decoder can handle.

            Returns:
                List[str]: A list of supported media type strings that this decoder can decode.
        """


    def decode_inst(self,inst : DCMInstance, requested_planar_config : int | None = None) -> DCMPixelData|None:

        """
            Decode a DICOM instance's pixel data into a standardized pixel data representation.

            This method processes the pixel data of a DICOM instance, decoding each frame
            and handling color space and planar configuration transformations.

            Args:
                inst (DCMInstance): The DICOM instance containing pixel data to decode.
                requested_planar_config (int, optional): Desired planar configuration for multi-sample pixel data.
                    Defaults to None, which uses the original planar configuration.

            Returns:
                DCMPixelData | None: Decoded pixel data as a DCMPixelData object, or None if no pixel data exists.

            Notes:
                - Supports single and multi-frame DICOM images
                - Handles RGB color space transformations
                - Preserves original image metadata during decoding
        """

        frames=[]
        params : Dict [str,Any] = {}

        if inst.pixel_data:

            params["samples_per_pixel"] = inst.pixel_data.samples_per_pixel
            params["photometric_interpretation"] = inst.pixel_data.photometric_interpretation
            params["rows"] = inst.pixel_data.rows
            params["columns"] = inst.pixel_data.columns
            params["bits_allocated"] = inst.pixel_data.bits_allocated
            params["bits_stored"] = inst.pixel_data.bits_stored
            params["high_bit"] = inst.pixel_data.high_bit
            params["planar_configuration"] = inst.pixel_data.planar_configuration
            params["requested_planar_config"] = requested_planar_config

            for frame in inst.pixel_data.frames:

                decoded_frame = self.decode_image(frame,**params)

                frames.append(decoded_frame.tobytes())


            photo_interpretation = inst.pixel_data.photometric_interpretation
            planar_configuration = inst.pixel_data.planar_configuration


            if inst.pixel_data.samples_per_pixel == 3 :

                photo_interpretation = "RGB"
                if requested_planar_config is not None:
                    planar_configuration = requested_planar_config
                else:
                    planar_configuration = 0

            pd = DCMPixelData(
                number_of_frames=inst.pixel_data.number_of_frames,
                transfer_syntax_uid=ExplicitVRLittleEndian,
                pixel_data_format="INT",
                pixel_representation = inst.pixel_data.pixel_representation,
                samples_per_pixel=inst.pixel_data.samples_per_pixel,
                photometric_interpretation=photo_interpretation,
                rows=inst.pixel_data.rows,
                columns=inst.pixel_data.columns,
                bits_allocated=inst.pixel_data.bits_allocated,
                bits_stored=inst.pixel_data.bits_stored,
                high_bit=inst.pixel_data.high_bit,
                planar_configuration=planar_configuration,
                frames=frames,
                smallest_image_pixel_value=inst.pixel_data.smallest_image_pixel_value,
                largest_image_pixel_value=inst.pixel_data.largest_image_pixel_value
            )  ## if we are doing decode, then we are not looking at palette color

            return pd

        return inst.pixel_data

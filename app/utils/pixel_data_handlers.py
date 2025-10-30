"""Pixel data handling utilities for DICOM STOW operations.

This module provides functions to parse and process pixel data for DICOM instances,
handling both compressed and uncompressed pixel data formats. It supports conversion
of various image formats to DICOM-compatible pixel data structures.
"""

import math
import logging
from typing import List
import numpy
import pydicom
from pydicom.uid import ExplicitVRLittleEndian
from app.schema.dicom_instance import DCMInstance
from app.codecs.codec_registry import CodecRegistry
from app.utils.dicom_media import DicomMediaPart
from app.utils.jpeg_utils import extract_jpeg_metadata, get_media_type_ts,\
                                get_photometric_interpretation

logger = logging.getLogger(__name__)

def parse_ps310_pixel_data(data : bytes, number_of_frames :int , transfer_syntax_uid : str) -> List[bytes]:
    """Parse PS 3.10 pixel data based on transfer syntax.

    Parses pixel data according to DICOM PS 3.10 standard, handling both
    compressed and uncompressed pixel data formats.

    Note: Will need to handle BITS_ALLOCATED == 1 and PhotometricInterpretation == 'YBR_FULL_422'
    Reference: https://github.com/pydicom/pydicom/blob/513509f512caaf4f534a3448be4e54ff8796e6cf/pydicom/pixel_data_handlers/numpy_handler.py

    Args:
        data (bytes): The pixel data bytes to parse
        number_of_frames (int): Number of frames in the pixel data
        transfer_syntax_uid (str): Transfer syntax UID for the pixel data

    Returns:
        list: List of frame data bytes
    """

    ## here we can convert to what ever format we want as well.
    ## check for floating point or double data
    ## check


    ## this works in all cases as we are just splitting frames
    ## only error case will be if BitsAllocated = 1.

    frame_data = None

    ## TODO: Need to remove the padding byte.

    if  transfer_syntax_uid ==  ExplicitVRLittleEndian:
        ## single or multi-frame data. Uncompressed
        ## split byte stream into n frames
        ## this does not handle padding or expected length
        frame_data = parse_uncompressed_bulk_pixel_data(data, number_of_frames)


    else: ## single or multi-frame data, compressed
        frame_data =  [ frame for frame in pydicom.encaps.generate_frames(data,number_of_frames=number_of_frames) ]
        logger.warning(frame_data[0][:10])
        ## we need to split the frames out

    return frame_data


def parse_uncompressed_bulk_pixel_data(data : bytes, number_of_frames : int ) -> List[bytes]:
    """Parse uncompressed bulk pixel data into frames.

    Splits uncompressed pixel data into individual frames based on the
    total data length and number of frames.

    Note: Will need to handle BITS_ALLOCATED == 1 and PhotometricInterpretation == 'YBR_FULL_422'

    Args:
        data (bytes): The uncompressed pixel data bytes
        number_of_frames (int): Number of frames to split the data into

    Returns:
        list: List of frame data bytes, each frame as bytes
    """

    frame_length = math.floor(len(data)/number_of_frames) ## works also in the case
    return  [data[offset:offset+frame_length] for offset in range(0,number_of_frames,frame_length)]

def parse_compressed_bulk_pixel_data(part : DicomMediaPart, instance : DCMInstance, \
                                     pixel_data_format : str, codec_registry : CodecRegistry) -> None:
    """Parse compressed bulk pixel data and update instance metadata.

    Processes compressed pixel data from various image formats (PNG, GIF, DICOM)
    and updates the DICOM instance with appropriate pixel data attributes.

    Args:
        part: The multipart data containing pixel data
        instance: The DICOM instance to update with pixel data
        pixel_data_format (str): The format of the pixel data
        codec_registry: Registry containing image decoders

    Returns:
        None: Updates the instance in-place
    """

    if part.content_type_str() in ["image/png","image/gif"]:
        ## tranform these into uncompressed objects
        #dcm_pixel_meta = codec_registry.decode_image_header(part.data,part.content_type_str())
        dcm_pixel = codec_registry.decode_png_gif(part.data,part.content_type_str())

        if instance.pixel_data is not None:
            ## we will make this into an RGB or mono image
            instance.pixel_data.transfer_syntax_uid = ExplicitVRLittleEndian
            instance.pixel_data.pixel_data_format = pixel_data_format
            if len(dcm_pixel.shape) == 3:
                instance.pixel_data.samples_per_pixel = dcm_pixel.shape[2]
                instance.pixel_data.photometric_interpretation = "RGB"
                instance.pixel_data.planar_configuration = 1

            else:
                instance.pixel_data.photometric_interpretation = "MONOCHROME2"
                instance.pixel_data.samples_per_pixel = 1

            ## MONOCHROME or RGB

            instance.pixel_data.rows = dcm_pixel.shape[0]
            instance.pixel_data.columns = dcm_pixel.shape[1]
            if dcm_pixel.dtype == numpy.uint8:
                instance.pixel_data.bits_allocated = 8
                instance.pixel_data.bits_stored = 8
                instance.pixel_data.high_bit = 7
            elif dcm_pixel.dtype == numpy.uint16:
                instance.pixel_data.bits_allocated = 16
                instance.pixel_data.bits_stored = 16
                instance.pixel_data.high_bit = 15

            instance.pixel_data.pixel_representation = 0
            instance.pixel_data.frames[0] = dcm_pixel.tobytes()

    elif part.content_type_str() in ["image/jpeg","image/jls","image/jp2","image/jpx","image/jphc","image/jxl"]:
        ## read the headers

        md = extract_jpeg_metadata(part.data)
        (media_type, transfer_syntax_uid) = get_media_type_ts(md) # pylint disable=unused-variable
        pi = get_photometric_interpretation(md)

        if instance.pixel_data is not None:
            instance.pixel_data.frames[0] = part.data
            ## copy all the other bits here
            instance.pixel_data.transfer_syntax_uid = transfer_syntax_uid

            instance.pixel_data.pixel_data_format = "INT" # has to be int
            instance.pixel_data.samples_per_pixel = md.components
            instance.pixel_data.photometric_interpretation = pi
            instance.pixel_data.planar_configuration = 0 ## TODO
            instance.pixel_data.rows = md.height
            instance.pixel_data.columns = md.width

            bits_stored = md.bits_per_sample

            if bits_stored % 8 == 0:
                bits_allocated = bits_stored
            else:
                bits_allocated = math.ceil(bits_stored / 8)*8

            instance.pixel_data.bits_allocated = bits_allocated
            instance.pixel_data.bits_stored = bits_stored
            instance.pixel_data.high_bit = bits_stored - 1

            instance.pixel_data.pixel_representation=0 # TODO this can be unsigned in certain situations


    else:
        raise NotImplementedError("Not implemented yet")


def parse_compressed_bulk_video_data(part : DicomMediaPart,instance : DCMInstance,pixel_data_format:str)->None:
    """
        parse video data
    """
    raise NotImplementedError("Not implemented yet")
   # if part.content_type_str() in ["image/png","image/gif"]:
        ## tranform these into uncompressed objects

   # else:
        ## read the headers

    #    instance.pixel_data.frames[0] = part.data
     #   pass
#    pass

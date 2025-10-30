"""
This module contains utilities for transcoding DICOM instances between transfer syntaxes.

This module provides functions for converting DICOM instances from one transfer syntax
to another using the codec registry system. It handles both decoding from compressed
formats and encoding to different compression formats.
"""

import logging
from pydicom.uid import ExplicitVRLittleEndian
from app.schema.dicom_instance import DCMInstance
from app.codecs.codec_registry import CodecRegistry

logger = logging.getLogger(__name__)

def convert_dcm(inst : DCMInstance, requested_transfer_syntax : str, codec_registry : CodecRegistry) -> DCMInstance:
    """
        Convert a DICOM instance to the requested transfer syntax.

        Transcodes DICOM pixel data from its current transfer syntax to the
        requested transfer syntax using the provided codec registry. Handles
        both decompression to uncompressed format and compression to various
        compressed formats.

        Args:
            inst: DICOM instance containing pixel data to be transcoded.
            requested_transfer_syntax (str): Target transfer syntax UID.
            codec_registry: Registry containing encoders and decoders for
                           various transfer syntaxes.

        Returns:
            The modified DICOM instance with pixel data in the requested
            transfer syntax.

        Note:
            For ExplicitVRLittleEndian, only decoding is performed with
            planar configuration 0. For other transfer syntaxes, both
            decoding and encoding are performed.
    """
    # run the codecs

    if codec_registry is not None:

        # decode inst

        if requested_transfer_syntax == ExplicitVRLittleEndian:
            # decode only for uncompressed format with planar configuration 0
            decoded_pixel_data = codec_registry.decode_inst(inst, 0)

            #logger.warning(decoded_pixel_data)
            inst.pixel_data = decoded_pixel_data
            #logger.warning("Frame count: %d, Frame 0 size: %d",
            #             len(decoded_pixel_data.frames), len(decoded_pixel_data.frames[0]))
        else:
            # decode with planar configuration 1, then encode to requested format
            decoded_pixel_data = codec_registry.decode_inst(inst, 1)
            if decoded_pixel_data:
                encoded_pixel_data = codec_registry.encode_inst(decoded_pixel_data, requested_transfer_syntax)
                inst.pixel_data = encoded_pixel_data

        return inst

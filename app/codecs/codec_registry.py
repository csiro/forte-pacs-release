"""
This module contains the CodecRegistry, which holds decoders and encoders
for transcoding.

"""
from typing import Dict
from numpy.typing import NDArray
from app.schema.dicom_instance import DCMInstance
from app.schema.dicom_pixel_data import DCMPixelData
from app.codecs.decoder import Decoder
from app.codecs.encoder import Encoder

class CodecRegistry:
    """
        Registry for managing DICOM image codecs.

        This class maintains collections of decoders and encoders for various
        DICOM transfer syntaxes and media types. It provides a central registry
        for codec management and automated selection of appropriate codecs
        based on transfer syntax UIDs and media types.
    """

    def __init__(self) -> None:
        """
            Initialize an empty codec registry.

            Creates empty dictionaries for storing decoders and encoders,
            keyed by their supported media types or transfer syntax UIDs.
        """
        self.decoders : Dict[str,Decoder] = {}
        self.encoders : Dict[str, Encoder]= {}



    def register_decoder(self,decoder : Decoder,media_types: str | None =None) -> None:
        """
            Register a decoder for specific media types.

            Args:
                decoder (Decoder): The decoder to register.
                media_types (str | None, optional): Specific media types to register the decoder for.
                    If None, registers the decoder for all its supported media types. Defaults to None.
        """

        decoder_media_types = decoder.decodable_mediatypes()

        for dd in decoder_media_types:

            if not media_types or dd in media_types:
                self.decoders[dd]=decoder


    def register_encoder(self,encoder : Encoder,media_types: str | None =None) -> None:
        """
            Register an encoder for specific media types.

            Args:
                encoder (Encoder): The encoder to register.
                media_types (str | None, optional): Specific media types to register the encoder for.
                    If None, registers the encoder for all its supported media types. Defaults to None.
        """

        encoder_media_types = encoder.encodable_mediatypes()

        for ee in encoder_media_types:
            if not media_types or ee in media_types:
                self.encoders[ee] = encoder

    def decode_png_gif(self,pixel_data: bytes,media_type:str) -> NDArray:
        """
            Decode a pixel data frame using the appropriate decoder based on the transfer syntax UID.

            Args:
                pixel_data: The pixel data to decode.
                media_type: The media type of the pixel data.

            Returns:
                The decoded pixel data.
        """
        if media_type not in ["image/png", "image/gif"]:
            raise NotImplementedError(f"Unsupported media type: {media_type}")

        decoded_frame = self.decoders[media_type].decode_image(pixel_data,requested_planar_config=1)
        return decoded_frame

    def decode_inst(self,inst:DCMInstance, requested_planar_config:int)-> DCMPixelData | None:
        """
            Decode an instance using the appropriate decoder based on the instance's transfer syntax UID.

            Args:
                inst: The instance to decode.
                requested_planar_config: The desired planar configuration for the decoded instance.

            Returns:
                The decoded instance with the specified planar configuration.
        """
        if not inst.pixel_data:
            return None
        if  inst.pixel_data.transfer_syntax_uid not in self.decoders.keys():
            return None
        return self.decoders[inst.pixel_data.transfer_syntax_uid].decode_inst(inst,requested_planar_config)


    def encode_inst(self,pixel_data: DCMPixelData,requested_media_type:str)-> DCMPixelData| None:
        """
            Encode an instance using the appropriate encoder based on the requested media type.

            Args:
                inst: The instance to encode.
                requested_media_type: The media type to encode the instance into.

            Returns:
                The encoded instance in the specified media type.
        """
        if requested_media_type not in self.encoders.keys():
            return None
        return self.encoders[requested_media_type].encode_inst(pixel_data,requested_media_type)

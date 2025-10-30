"""
    Schema for dicom instance pixel data that is used throughout the application.
"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# most important section
# https://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_8.2.html

class DCMPixelData(BaseModel):

    """Represents a DICOM instance pixel data.

    The DCMPixelData class contains metadata about the DICOM instance pixel data,
    such as the number of frames, stored transfer syntax, rows, columns and the pixel representation.

    Attributes:
        number_of_frames (int): The number of frames in the image.
        transfer_syntax_uid (Optional[str]): The transfer syntax UID.
        pixel_data_format (str): The pixel data format.
        samples_per_pixel (int): The number of samples per pixel.
        photometric_interpretation (str): The photometric interpretation.
        rows (int): The number of rows in the image.
        columns (int): The number of columns in the image.
        bits_allocated (int): The number of bits allocated.
        bits_stored (int): The number of bits stored.
        high_bit (int): The high bit.
        pixel_representation (int): The pixel representation.
        planar_configuration (Optional[int]): The planar configuration.
        frames (List[bytes]): The frames of the image.
        smallest_image_pixel_value (Optional[int]): The smallest image pixel value.
        largest_image_pixel_value (Optional[int]): The largest image pixel value.
        pixel_padding_range_limit (Optional[int]): The pixel padding range limit.
        red_palette_color_lookup_table_descriptor Optional[bytes]:
        green_palette_color_lookup_table_descriptor Optional[bytes]:
        blue_palette_color_lookup_table_descriptor Optional[bytes]:
        red_palette_color_lookup_table_data (Optional[List[int]]): The red palette color lookup table data.
        green_palette_color_lookup_table_data (Optional[List[int]]): The green palette color lookup table data.
        blue_palette_color_lookup_table_data (Optional[List[int]]): The blue palette color lookup table data.

    """

    model_config = ConfigDict(ser_json_bytes='base64',val_json_bytes='base64')  # type: ignore
    number_of_frames:int # number of frames in the image
    transfer_syntax_uid: Optional[str] = None # transfer syntax UID
    pixel_data_format: str ## float and double datasets are only native

    samples_per_pixel : int # samples per pixel
    photometric_interpretation: str
    rows: int
    columns : int
    bits_allocated : int
    bits_stored : int
    high_bit : int
    pixel_representation : int
    planar_configuration : Optional[int] = None
    frames: List[bytes] # list of frames as bytes.

    smallest_image_pixel_value: Optional[int] = None
    largest_image_pixel_value:  Optional[int] = None
    #pixel_padding_range_limit: Optional[int]
    red_palette_color_lookup_table_descriptor: Optional[List[int]] = None
    blue_palette_color_lookup_table_descriptor: Optional[List[int]] = None
    green_palette_color_lookup_table_descriptor: Optional[List[int]] = None

    red_palette_color_lookup_table_data: Optional[bytes] = None
    blue_palette_color_lookup_table_data: Optional[bytes] = None
    green_palette_color_lookup_table_data: Optional[bytes] = None




    #icc_profile: Optional[bytes]
    #color_space: Optional[str]

    #extended_offset_table: Optional [bytes]
    #extended_offset_table_lengths: Optional [bytes]

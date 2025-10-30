"""
    Schema for dicom instance that is used throughout the application.
"""

from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict
from app.schema.dicom_pixel_data import DCMPixelData




class DCMInstance(BaseModel):
    """Represents a DICOM instance, which is a single DICOM object within a DICOM series.

    The DCMInstance class contains metadata about the DICOM instance, such as the study UID,
    series UID, instance UID, SOP class UID, and optional pixel data and other bulk data.

    Attributes:
        study_uid (str): The unique identifier for the DICOM study.
        series_uid (str): The unique identifier for the DICOM series.
        instance_uid (str): The unique identifier for the DICOM instance.
        meta_data (str): The DICOM instance metadata as a string.
            This is all tags that are not pixel or bulk data.
            Tags related to pixel data are stored in the pixel_data attribute.
        sop_class_uid (str): The unique identifier for the DICOM SOP class.
        pixel_data (Optional[DCMPixelData]): The DICOM pixel data, if available.
        other_bulk_data (Optional[Dict[str, bytes]]): Any other bulk data associated with the DICOM instance.
        encap_document_mediatype (Optional[str]): The media type of any encapsulated document.
    """
    model_config = ConfigDict(ser_json_bytes='base64',val_json_bytes='base64')  # type: ignore

    study_uid: str
    series_uid: str
    instance_uid: str

    # keep as string
    meta_data: str

    # what kind of dicom instance is this
    sop_class_uid: str

    # we might have some dicom instances without pixel data
    # therefore this is optional with a default value of None
    pixel_data: Optional[DCMPixelData] = None

    # this is other bulk data and includes encap documents
    # optional because if the dataset contains image data,
    # it may not have other bulkdata
    other_bulk_data: Optional[Dict[str,bytes]] = None

    # if this a document type, encap mimetype is here
    encap_document_mediatype: Optional[str] = None

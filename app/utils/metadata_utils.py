"""
    Utility functions for metadata
"""

import json
from typing import Dict, Any
from app.schema.dicom_instance import DCMInstance

def combine_metadata(instance : DCMInstance) -> Dict[str,Any]:
    """
        Combine the general and pixel metadata into a single dictionary

        Args:
            inst (DCMInstance): DICOM instance containing frames and metadata.

        Returns:
            Dict[str, Any]: Combined metadata dictionary.
    """
    meta_data : Dict[str, Any] = json.loads(instance.meta_data)
    if instance.pixel_data is not None:
        meta_data["00280010"] = {"Value":[instance.pixel_data.rows]}
        meta_data["00280011"] = {"Value":[instance.pixel_data.columns]}
        meta_data["00280100"] = {"Value":[instance.pixel_data.bits_allocated]}

    return meta_data

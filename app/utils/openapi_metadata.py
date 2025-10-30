"""
Contains response metadata for openapi routes. In turn used to generate capability statements

"""

from typing import Any
from useful_types import SupportsKeysAndGetItem

stow_request_representation ={
     "requestBody": {
            "content": {
                'multipart/related; type="application/dicom"': {},

            },
            "required": True,
        },
}

standard_response : SupportsKeysAndGetItem[int | str, dict[str, Any]]= {
    200: {
        "description": "OK",
        "content": {
            'multipart/related;type="application/dicom+xml"':{},
            'multipart/related;type="application/dicom+json"':{},
        }
    }
}

ni_resp : SupportsKeysAndGetItem[int | str, dict[str, Any]]= {
    501: {
        "description": "Not implemented",
    }
}

rend_resp : SupportsKeysAndGetItem[int | str, dict[str, Any]]= {
    200: {
        "description": "OK",
        "content": {
            'image/png':{},
            'image/gif':{},
            'image/jpeg':{},
            'image/jp2':{}
        }
    }
}


inst_resp : SupportsKeysAndGetItem[int | str, dict[str, Any]]= {
    200: {
        "description": "OK",
        "content": {
            'multipart/related; type="application/dicom"':{}
        }
    }
}



bd_resp: SupportsKeysAndGetItem[int | str, dict[str, Any]] = {
    200: {
        "description": "OK",
        "content": {
            'multipart/related;type="application/octet-stream"':{},
            'multipart/related;type="application/dicom"':{}
        }
    }
}
